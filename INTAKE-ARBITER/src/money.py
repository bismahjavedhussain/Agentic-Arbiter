# -*- coding: utf-8 -*-
"""MONEY -- chiller-hours avoided, priced. Every input opened and read.  ZERO API CALLS.

    python money.py             # build demo/money.json and print the table
    python money.py selftest    # the arithmetic, checked by hand-computed cases

--------------------------------------------------------------------------------------------
WHY THIS MODULE DID NOT EXIST UNTIL NOW
--------------------------------------------------------------------------------------------
The project's standing position was: no dollar or kWh figure anywhere, because the C-to-kWh
conversion could not be sourced from a primary document. That was the right call while it was true.
It is no longer true for ONE term -- the chiller compressor -- and this module does only that term.

Two documents were downloaded and parsed in this repository, not read from a search result:

  ELECTRICITY PRICE   EIA, "2024 Total Electric Industry- Average Retail Price (cents/kWh)",
                      forms EIA-861 schedules 4A-D / 861S / 861U. Fetched as PDF, text extracted
                      with pypdf, the Virginia and Illinois rows printed verbatim:
                        Virginia   residential 14.41  commercial 8.72  industrial 8.99  total 10.62
                        Illinois   residential 15.87  commercial 11.81 industrial 8.83  total 12.21
                      https://www.eia.gov/electricity/sales_revenue_price/pdf/table_4.pdf
                      And EIA Table 5.6.A, May 2026, parsed from the .xlsx AS A ZIP OF XML (no
                      spreadsheet library, no summarising model): Virginia commercial 10.84,
                      industrial 10.53; Illinois commercial 15.36, industrial 10.20.
                      https://www.eia.gov/electricity/monthly/xls/table_5_06_a.xlsx

  CHILLER EFFICIENCY  PNNL-29674, "ANSI/ASHRAE/IES Standard 90.1-2019 Performance Rating Method
                      Reference Manual", page 221 (PDF page 236), Table 82 "Minimum Efficiency
                      Requirements for Water Chilling Packages", which reproduces Standard
                      90.1-2019 Table G3.5.3. Read by printing PDF page 236 in full.
                      Water cooled, electrically operated, > 300 tons:
                        centrifugal        0.576 kW/ton full load   0.549 kW/ton IPLV.IP
                        screw and scroll   0.639 kW/ton full load   0.572 kW/ton IPLV.IP
                      Rated at ARI 550/590 conditions: 44 F leaving chilled fluid, 2.4 gpm/ton
                      evaporator, 85 F entering condenser fluid, 3.0 gpm/ton condenser.
                      https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-29674.pdf

`money-sources.md` in the repository root holds the verbatim quotes, the fetch method for each, and
the full limits list. Read it before quoting any number from here.

--------------------------------------------------------------------------------------------
THE UNIT, AND WHY IT IS NOT DOLLARS PER YEAR
--------------------------------------------------------------------------------------------
EVERYTHING IS PER MEGAWATT OF IT LOAD. This project has never measured a data centre's size, and
inventing one would be a hard-coded constant that multiplies the headline -- the worst kind. A reader
who knows their own IT load multiplies once.

--------------------------------------------------------------------------------------------
NOTHING IS CHOSEN. BOTH CONVERSION FACTORS ARE SWEPT.
--------------------------------------------------------------------------------------------
4 published prices x 4 published chiller efficiencies x every ladder and sensitivity row, and NO ROW
IS COLLAPSED. Averaging across incomparable plant settings is the mistake `agent._summarise` exists
to avoid, and it would be worse here, where the axes are a tariff and a machine.

--------------------------------------------------------------------------------------------
WHAT THIS IS NOT -- and the code refuses to let the file be read without it
--------------------------------------------------------------------------------------------
  1. THE COMPRESSOR ONLY. Free cooling stops the compressor. It does NOT stop the CRAH fans, the
     chilled-water pumps, the condenser pumps or the tower fans, and an airside economizer moves MORE
     air, so fan power can RISE. None of that is netted off, because this agent does not measure it.
     The figure is an UPPER BOUND and the unmeasured term has the opposite sign.
  2. CODE MINIMUM IS THE OPTIMISTIC END. Standard 90.1 is a floor; hyperscale plants beat it, and a
     better chiller saves less money per hour switched off.
  3. FULL LOAD OVERSTATES the draw at the moment free cooling is possible -- free cooling happens
     when it is COOL, and a chiller at a cool condenser runs below its rated full-load kW/ton. IPLV
     is the lower published figure but it is an annual-weighted metric under AHRI's assumed load
     profile, not the part-load point that coincides with free-cooling weather. Neither end is right;
     both are published, so both are swept.
  4. STATE-AVERAGE TARIFFS, not the site's. A Loudoun County campus buys on a large-general-service
     contract that is not public.
  5. EVERY CAVEAT ON THE HOURS IS INHERITED. The refusal guard is priced at -3,124 h/yr where it
     fires; the unanchored row is NEGATIVE. Those rows appear here with their signs intact.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import metros as M                                                  # noqa: E402

# ============================================================================
# THE SOURCED CONSTANTS. Every one carries its document, and every one is swept.
# ============================================================================
# 1 ton of refrigeration = 12,000 Btu/h exactly = 3.516852842 kW. This is the ONE step with no PDF to
# open, because it is a definition rather than a measurement. Written out so it can be checked by
# hand: 12000 Btu/h x 1055.05585262 J/Btu / 3600 s/h = 3516.85 W.
BTU_PER_HOUR_PER_TON = 12000.0
JOULES_PER_BTU = 1055.05585262          # international table Btu, exact by definition
KW_PER_TON = BTU_PER_HOUR_PER_TON * JOULES_PER_BTU / 3600.0 / 1000.0

# PNNL-29674 Table 82 (ASHRAE 90.1-2019 Table G3.5.3), water cooled, electrically operated,
# > 300 tons -- the band that applies at and above ~1.06 MW of IT load. All four published values.
CHILLER_KW_PER_TON = [
    {"label": "centrifugal, IPLV.IP", "kw_per_ton": 0.549, "type": "centrifugal", "rating": "IPLV"},
    {"label": "centrifugal, full load", "kw_per_ton": 0.576, "type": "centrifugal", "rating": "FL"},
    {"label": "screw/scroll, IPLV.IP", "kw_per_ton": 0.572, "type": "positive displacement",
     "rating": "IPLV"},
    {"label": "screw/scroll, full load", "kw_per_ton": 0.639, "type": "positive displacement",
     "rating": "FL"},
]

# EIA. Two vintages and two sectors, spanning the two metros that ship.
ELECTRICITY_CENTS_PER_KWH = [
    {"label": "Virginia commercial, 2024 annual", "cents": 8.72, "state": "VA",
     "sector": "commercial", "vintage": "2024 annual", "source": "EIA table_4.pdf"},
    {"label": "Virginia industrial, 2024 annual", "cents": 8.99, "state": "VA",
     "sector": "industrial", "vintage": "2024 annual", "source": "EIA table_4.pdf"},
    {"label": "Virginia commercial, May 2026", "cents": 10.84, "state": "VA",
     "sector": "commercial", "vintage": "May 2026", "source": "EIA Table 5.6.A"},
    {"label": "Virginia industrial, May 2026", "cents": 10.53, "state": "VA",
     "sector": "industrial", "vintage": "May 2026", "source": "EIA Table 5.6.A"},
    {"label": "Illinois commercial, 2024 annual", "cents": 11.81, "state": "IL",
     "sector": "commercial", "vintage": "2024 annual", "source": "EIA table_4.pdf"},
    {"label": "Illinois industrial, 2024 annual", "cents": 8.83, "state": "IL",
     "sector": "industrial", "vintage": "2024 annual", "source": "EIA table_4.pdf"},
    {"label": "Illinois commercial, May 2026", "cents": 15.36, "state": "IL",
     "sector": "commercial", "vintage": "May 2026", "source": "EIA Table 5.6.A"},
    {"label": "Illinois industrial, May 2026", "cents": 10.20, "state": "IL",
     "sector": "industrial", "vintage": "May 2026", "source": "EIA Table 5.6.A"},
]

# LBNL 2024, page 47, read directly. CONTEXT ONLY -- never used as a multiplier, because attributing
# the right share of PUE overhead to the chiller needs a breakdown the report does not give.
LBNL_PUE = {"average_2023": 1.4, "projected_2028_low": 1.15, "projected_2028_high": 1.35,
            "source": "LBNL 2024 United States Data Center Energy Usage Report, p. 47"}

SOURCES = {
    "electricity_price": [
        {"title": "2024 Total Electric Industry- Average Retail Price (cents/kWh)",
         "publisher": "U.S. Energy Information Administration",
         "forms": "EIA-861 schedules 4A-D, EIA-861S, EIA-861U",
         "url": "https://www.eia.gov/electricity/sales_revenue_price/pdf/table_4.pdf",
         "how_read": "downloaded and text-extracted with pypdf; the Virginia and Illinois rows "
                     "printed verbatim"},
        {"title": "Table 5.6.A. Average Price of Electricity to Ultimate Customers by End-Use "
                  "Sector, by State, May 2026 and 2025 (Cents per Kilowatthour)",
         "publisher": "U.S. Energy Information Administration",
         "url": "https://www.eia.gov/electricity/monthly/xls/table_5_06_a.xlsx",
         "how_read": "the .xlsx parsed as a zip of XML with zipfile and xml.etree -- no spreadsheet "
                     "library and no summarising model"}],
    "chiller_efficiency": [
        {"title": "PNNL-29674, ANSI/ASHRAE/IES Standard 90.1-2019 Performance Rating Method "
                  "Reference Manual, p. 221, Table 82 'Minimum Efficiency Requirements for Water "
                  "Chilling Packages' (reproducing Standard 90.1-2019 Table G3.5.3)",
         "publisher": "Pacific Northwest National Laboratory, U.S. Department of Energy",
         "url": "https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-29674.pdf",
         "how_read": "downloaded, pypdf text extraction, PDF page 236 printed in full and read in "
                     "place",
         "note": "ASHRAE 90.1 itself is paywalled. This is a free DOE national-laboratory "
                 "publication reproducing the requirement tables -- the standard's values at one "
                 "remove, and the remove is stated.",
         "rating_conditions": "ARI 550/590: 44 F leaving chilled fluid, 2.4 gpm/ton evaporator, "
                              "85 F entering condenser fluid, 3.0 gpm/ton condenser"}],
    "context_only": [
        {"title": "2024 United States Data Center Energy Usage Report",
         "publisher": "Lawrence Berkeley National Laboratory for the U.S. DOE",
         "url": "https://eta-publications.lbl.gov/sites/default/files/2024-12/"
                "lbnl-2024-united-states-data-center-energy-usage-report_1.pdf",
         "how_read": "downloaded, all 79 pages text-extracted and grepped",
         "what_it_gives": "average PUE 1.4 in 2023, projected 1.15-1.35 by 2028 (p. 47)",
         "what_it_does_NOT_give": "any chiller kW/ton, COP or IPLV figure -- checked by grepping "
                                  "every page for kW/ton, COP, IPLV and 'chiller efficien'; the "
                                  "only hits were bibliographic"}],
}

NOT_CLAIMED = [
    "The chiller COMPRESSOR only. Fans, chilled-water pumps, condenser pumps and cooling-tower fans "
    "keep running, and an airside economizer moves MORE air, so fan power can rise. The unmeasured "
    "term has the OPPOSITE SIGN, so this is an upper bound.",
    "Code-minimum chiller efficiency is the OPTIMISTIC end: Standard 90.1 is a floor, hyperscale "
    "plants beat it, and a better chiller saves less per hour switched off.",
    "Full-load kW/ton OVERSTATES the draw at the moment free cooling is available, because free "
    "cooling happens when it is cool and a chiller at a cool condenser runs below its rating. IPLV "
    "is the lower published number but is an annual-weighted metric under AHRI's assumed load "
    "profile, not the part-load point free-cooling weather sits at.",
    "The heat rejected is APPROXIMATED by the IT load. UPS, PDU and lighting losses inside the "
    "envelope add to it; some overhead sits outside the cooled space, so scaling by full PUE would "
    "overshoot. No PUE multiplier is applied.",
    "EIA STATE-SECTOR AVERAGES, not the site's tariff. A Loudoun County campus buys on a "
    "large-general-service contract that is not public.",
    "No carbon, no water, no maintenance and no demand charges. Tower water use moves the OTHER way "
    "when the chiller runs less.",
    "Every caveat on the hours is inherited: the headline is conditional on the bank sitting on the "
    "long facade (the refusal guard is priced at -3,124 h/yr where it fires) and the unanchored row "
    "is NEGATIVE. Those rows appear here with their signs intact.",
]


# ============================================================================
def chiller_kw_per_mw_it(kw_per_ton):
    """Chiller electrical power drawn to reject 1 MW of heat, in kW.

    1 MW / (kW per ton) tons, times kW per ton of compressor power. Written as two named steps
    rather than one collapsed constant so a reader can check each.
    """
    tons = 1000.0 / KW_PER_TON
    return tons * kw_per_ton


def price_row(hours_per_year, kw_per_ton, cents_per_kwh):
    """One cell: kWh and dollars per MW of IT load per year. Signs are preserved -- a NEGATIVE hours
    row must produce a NEGATIVE saving, because that row is the agent losing to the incumbent."""
    kw = chiller_kw_per_mw_it(kw_per_ton)
    kwh = hours_per_year * kw
    return {"chiller_kw_per_mw_it": kw, "kwh_per_mw_it_per_year": kwh,
            "usd_per_mw_it_per_year": kwh * cents_per_kwh / 100.0}


def hours_rows(backtest):
    """Every hours figure the five-year run produced, with its own label and provenance.

    Read from backtest.json rather than restated, so a ladder row that changes changes here too --
    the fourth hard-coded narrative in this project asserted a stale hours figure (gotcha #67).
    """
    rows = []
    for r in backtest["n56_audit"]:
        if str(r["step"]).startswith("C "):
            rows.append({"family": "five-year ladder", "label": r["step"][2:],
                         "hours_per_year": r["gain_h_per_year"],
                         "coverage": r.get("coverage_agent_bound")})
    for r in backtest["sensitivity"]["rows"]:
        rows.append({"family": "12-axis sensitivity", "is_base": bool(r["is_base"]),
                     "label": "%s = %s" % (r["axis"], r["value"]),
                     "axis": r["axis"], "value": str(r["value"]),
                     "hours_per_year": r["gain_h_per_year"],
                     "coverage": r.get("coverage_agent_bound")})
    return rows


def prices_for_metro(k=None):
    """The EIA rows for THIS site's state. Chicago is Illinois; Ashburn and Dulles are Virginia.

    Sweeping Virginia's tariff over a Chicago site would price Illinois electricity at a Virginia
    rate -- and Illinois commercial is 11.81 against Virginia's 8.72, a 35 % difference, so it is
    not a rounding matter. If a state has no row here the sweep falls back to ALL of them and the
    fallback is reported, rather than silently pricing the wrong grid.
    """
    st = M.metro(k)["state"]
    own = [p for p in ELECTRICITY_CENTS_PER_KWH if p["state"] == st]
    return (own, st) if own else (ELECTRICITY_CENTS_PER_KWH, None)


def build(backtest, prices=None):
    prices = prices or ELECTRICITY_CENTS_PER_KWH
    rows = hours_rows(backtest)
    cells = []
    for h in rows:
        for ch in CHILLER_KW_PER_TON:
            for pr in prices:
                p = price_row(h["hours_per_year"], ch["kw_per_ton"], pr["cents"])
                cells.append({"hours_label": h["label"], "family": h["family"],
                              "hours_per_year": h["hours_per_year"],
                              "chiller": ch["label"], "kw_per_ton": ch["kw_per_ton"],
                              "price_label": pr["label"], "cents_per_kwh": pr["cents"],
                              **p})
    return rows, cells


def selftest():
    """The arithmetic, against values computed INDEPENDENTLY of this module.

    The expectations below were produced with Python's `decimal` at 30 significant digits, in a
    separate process, from the quoted source values -- not by running this module and pasting what it
    said, which would test nothing. That mattered: three of them were wrong on the first attempt,
    because they had been derived by hand from the ROUNDED intermediate 163.782798 rather than from
    full precision. The self-test caught my arithmetic, not the code's.
    """
    ok, bad = 0, []

    def want(label, got, expect, tol):
        nonlocal ok
        if abs(got - expect) <= tol:
            ok += 1
        else:
            bad.append("%s: got %.6f, expected %.6f" % (label, got, expect))

    # 12000 * 1055.05585262 / 3600 / 1000 = 3.5168528420...
    want("kW per ton of refrigeration", KW_PER_TON, 3.5168528420, 1e-9)
    # 1000 / 3.51685284206666... = 284.345136093995...
    want("tons to reject 1 MW", 1000.0 / KW_PER_TON, 284.345136094, 1e-8)
    # 284.345136094 x each published kW/ton
    want("centrifugal FL kW per MW IT", chiller_kw_per_mw_it(0.576), 163.782798, 1e-6)
    want("centrifugal IPLV kW per MW IT", chiller_kw_per_mw_it(0.549), 156.105480, 1e-6)
    want("screw IPLV kW per MW IT", chiller_kw_per_mw_it(0.572), 162.645418, 1e-6)
    want("screw FL kW per MW IT", chiller_kw_per_mw_it(0.639), 181.696542, 1e-6)
    # 405.7 h x 163.782798... kW = 66446.681307 kWh; at 8.72 c/kWh = $5794.150610
    c = price_row(405.7, 0.576, 8.72)
    want("405.7 h -> kWh", c["kwh_per_mw_it_per_year"], 66446.681307, 1e-5)
    want("405.7 h -> USD at 8.72 c", c["usd_per_mw_it_per_year"], 5794.150610, 1e-5)
    # A NEGATIVE hours row must stay negative. -156.0 h is the unanchored ladder row, and a sign
    # dropped here would turn the agent's worst result into a saving.
    n = price_row(-156.0, 0.576, 8.72)
    want("negative hours stay negative", n["usd_per_mw_it_per_year"], -2227.970163, 1e-5)
    if n["usd_per_mw_it_per_year"] >= 0:
        bad.append("a negative hours row produced a non-negative saving")
    else:
        ok += 1

    print("=" * 78)
    print("MONEY SELF-TEST: %d passed, %d failed" % (ok, len(bad)))
    for b in bad:
        print("   FAILED: %s" % b)
    print("=" * 78)
    return 0 if not bad else 1


def main():
    from agent import banner, say
    banner("MONEY   chiller-hours priced, every input opened and read.  [no API calls]")
    bp = M.demo_path("backtest.json")
    if not os.path.exists(bp):
        say("   backtest.json missing -- run `python run_all.py` first.")
        return 2
    backtest = json.load(open(bp, encoding="utf-8"))
    prices, own_state = prices_for_metro()
    say("\n   site           : %s  (%s)" % (M.metro()["label"], M.metro()["state"]))

    say("\n   THE TWO CONVERSION FACTORS, BOTH SWEPT, NEITHER CHOSEN")
    say("      chiller power per MW of IT load, from PNNL-29674 Table 82 (ASHRAE 90.1-2019):")
    for ch in CHILLER_KW_PER_TON:
        say("         %-26s %.3f kW/ton  ->  %7.2f kW per MW of IT"
            % (ch["label"], ch["kw_per_ton"], chiller_kw_per_mw_it(ch["kw_per_ton"])))
    say("      electricity price, from EIA -- %s:"
        % ("the %s rows, this site's own state" % own_state if own_state
           else "ALL rows, because this site's state has none"))
    for pr in prices:
        say("         %-34s %5.2f cents/kWh" % (pr["label"], pr["cents"]))
    say("      1 ton of refrigeration = 12,000 Btu/h = %.7f kW  (a definition, not a measurement)"
        % KW_PER_TON)

    rows, cells = build(backtest, prices)
    say("\n   %d hours rows x %d chiller efficiencies x %d prices = %d cells, none collapsed"
        % (len(rows), len(CHILLER_KW_PER_TON), len(prices), len(cells)))

    say("\n   THE FIVE-YEAR LADDER, PRICED. Range is across all %d price x chiller combinations."
        % (len(CHILLER_KW_PER_TON) * len(prices)))
    say("      %-46s %10s %12s %s" % ("step", "h/yr", "kWh/MW-IT", "USD per MW of IT per year"))
    for h in rows:
        if h["family"] != "five-year ladder":
            continue
        sub = [c for c in cells if c["hours_label"] == h["label"]
               and c["family"] == "five-year ladder"]
        lo = min(c["usd_per_mw_it_per_year"] for c in sub)
        hi = max(c["usd_per_mw_it_per_year"] for c in sub)
        kwh = [c["kwh_per_mw_it_per_year"] for c in sub]
        # `%`-formatting has no thousands flag -- `%+,.0f` raises. format() does.
        say("      %-46s %+10.1f %12s %s"
            % (h["label"][:46], h["hours_per_year"],
               "%s-%s" % (format(round(min(kwh)), ","), format(round(max(kwh)), ",")),
               "%+s to %+s" % (format(round(lo), ","), format(round(hi), ","))))

    base = [r for r in backtest["sensitivity"]["rows"] if r["is_base"]]
    if base:
        b = base[0]["gain_h_per_year"]
        va = price_row(b, 0.576, 8.72)
        say("\n   THE SHIPPED CONFIGURATION, said the honest way:")
        say("      %+.1f chiller-hours avoided per MW of IT load per year." % b)
        say("      At ASHRAE 90.1-2019's MINIMUM centrifugal chiller (0.576 kW/ton full load) and")
        say("      EIA's 2024 Virginia commercial average (8.72 cents/kWh): %s kWh, about $%s"
            % (format(round(va["kwh_per_mw_it_per_year"]), ","),
               format(round(va["usd_per_mw_it_per_year"]), ",")))
        say("      per MW of IT load per year -- COMPRESSOR ENERGY ONLY, at a CODE-MINIMUM chiller,")
        say("      on a STATE-AVERAGE tariff. All three qualifications make the real number smaller.")

    say("\n   WHAT IS NOT CLAIMED (also written into money.json, so the file cannot be read")
    say("   without it):")
    for n in NOT_CLAIMED:
        say("      - %s" % n)

    out = {"generated_by": "INTAKE-ARBITER/src/money.py", "api_calls_made": 0,
           "unit": "per megawatt of IT load per year -- this project has never measured a data "
                   "centre's size and will not invent one",
           "kw_per_ton_of_refrigeration": KW_PER_TON,
           "chiller_efficiencies_swept": CHILLER_KW_PER_TON,
           "metro": {"key": M.metro_key(), "label": M.metro()["label"],
                     "state": M.metro()["state"]},
           "electricity_prices_swept": prices,
           "electricity_prices_are_this_states_own": bool(own_state),
           "chiller_kw_per_mw_it": {ch["label"]: chiller_kw_per_mw_it(ch["kw_per_ton"])
                                    for ch in CHILLER_KW_PER_TON},
           "lbnl_pue_context_only": LBNL_PUE,
           "sources": SOURCES,
           "not_claimed": NOT_CLAIMED,
           "hours_rows": rows, "cells": cells}
    p = M.demo_path("money.json")
    json.dump(out, open(p, "w", encoding="utf-8"), allow_nan=False)
    say("\n   wrote %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if len(sys.argv) > 1 and sys.argv[1] == "selftest" else main())
