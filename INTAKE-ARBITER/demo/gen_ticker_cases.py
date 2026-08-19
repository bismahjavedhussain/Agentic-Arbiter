# -*- coding: utf-8 -*-
"""Write ticker_cases.json: stage-event tapes scored by the PYTHON ticker, so that
`node verify_browser_ticker.js` can check the browser's renderer against them.

TWO KINDS OF FIXTURE, because two different things are duplicated across the language boundary.

  1. FORMATTER VALUES. `tkFormat` in index.html mirrors `ticker.fmt_value`. The corners that
     actually differ between the two languages are not obvious, so they are enumerated rather than
     reasoned about: negative zero, exact halves at several precisions, values whose decimal
     expansion is not representable in binary, and the errors both must raise.

  2. WHOLE TAPES. `tickerFor` mirrors `ticker.hour_stream`, and what is duplicated there is the
     BRANCHING -- calm versus a real bearing, refused, a mode change versus a hold, a covered bound
     versus a missed one. So the fixture set is chosen to COVER EVERY BRANCH: this script searches
     the case days and configurations for hours that exercise each hour-template code, and fails if
     any template cannot be reached. A fixture set that never exercises a branch is exactly the hole
     that let verify_browser_decision.js report PASS while the unanchored path was 32 % wrong.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import explain as ex                                          # noqa: E402
import ticker as tk                                           # noqa: E402
from agent import plan                                        # noqa: E402

DEMO = HERE
trace = json.load(open(os.path.join(DEMO, "trace.json"), encoding="utf-8"))
backtest = json.load(open(os.path.join(DEMO, "backtest.json"), encoding="utf-8"))

# ---- 1. the formatter -----------------------------------------------------------------------
FORMAT_PROBES = [
    ("KIAD", ""), (True, ""), (False, ""),
    (0, ","), (1, ","), (999, ","), (1000, ","), (17862, ","), (120960, ","), (-43763, ","),
    (0.0, ".4f"), (-0.0, ".4f"), (-0.0, "+.4f"), (0.0, "+.4f"),
    (0.5, ".0f"), (1.5, ".0f"), (2.5, ".0f"), (-0.5, ".0f"), (-1.5, ".0f"),
    (0.125, ".2f"), (0.135, ".2f"), (0.145, ".2f"), (2.675, ".2f"),
    (0.35497, ".4f"), (0.1905, "+.4f"), (-0.7394, "+.4f"), (-3.7126856119135600, "+.4f"),
    (29.509799, ".3f"), (65.5898928824693, ".1f"), (0.9016955349389881, ".4f"),
    (1e-9, ".4f"), (-1e-9, ".4f"), (-1e-9, "+.4f"), (99.99999, ".4f"), (99.99999, ".2f"),
]
formatter = []
for v, spec in FORMAT_PROBES:
    formatter.append([v, spec, tk.fmt_value(v, spec)])

# ---- 2. the tapes ---------------------------------------------------------------------------
CONFIGS = [
    dict(ex.BASE_CFG),
    dict(ex.BASE_CFG, limit_c=24.0),
    dict(ex.BASE_CFG, limit_c=27.0, notice_h=6, skill=0.0),
    dict(ex.BASE_CFG, notice_h=0, skill=0.0),
    dict(ex.BASE_CFG, anchor="none", offset_day=None),
    dict(ex.BASE_CFG, anchor="none", offset_day="2026-08-16"),
    dict(ex.BASE_CFG, bank_mode="facing"),
    dict(ex.BASE_CFG, bank_mode="facing", limit_c=27.0),
    dict(ex.BASE_CFG, switch_budget=1, min_dwell_h=1),
    dict(ex.BASE_CFG, dewpoint_limit_c=None),
]
cases = [c["name"] for c in trace["cases"]["cases"] if c["day"]]

# Search every (case, config, hour) once, recording which branch each hour fires. Then keep a
# covering set plus a spread, rather than the first N -- which would all have been midnight in March.
found = {}                      # hour-template code -> list of candidate fixtures
allrows = []
for case in cases:
    for ci, cfg in enumerate(CONFIGS):
        st = ex.state_from_trace(trace, case, cfg)
        extra = tk._hour_extra(trace, case, cfg, backtest)
        modes, _f, _sw = plan(st["safe"], cfg["switch_budget"], cfg["min_dwell_h"])
        offday = cfg.get("offset_day")
        if cfg["anchor"] == "none" and offday is None:
            offday = trace["cases"]["fg_offsets"][0]["date"]
        for h in range(len(st["safe"])):
            events = tk.hour_stream(st, cfg, modes, st["safe"], h, extra)
            row = {
                "label": "%s/cfg%d/h%02d" % (case, ci, h),
                "hour_index": h,
                "browser_cfg": {
                    "c_case": case, "c_limit": cfg["limit_c"], "c_notice": cfg["notice_h"],
                    "c_anchor": cfg["anchor"], "c_skill": cfg["skill"],
                    "c_bank": cfg["bank_mode"], "c_budget": cfg["switch_budget"],
                    "c_dwell": cfg["min_dwell_h"],
                    "c_wb": "off" if cfg["dewpoint_limit_c"] is None else cfg["dewpoint_limit_c"],
                    "c_aq": "off" if cfg["aq_limit_idx"] is None else cfg["aq_limit_idx"],
                    "c_offday": offday or "",
                },
                "events": [{"code": e["code"], "text": e["text"]} for e in events],
            }
            allrows.append(row)
            for e in events:
                found.setdefault(e["code"], []).append(len(allrows) - 1)

hour_codes = [c for c in tk.ALL_TEMPLATES if c.startswith("hour.")]
missing = [c for c in hour_codes if c not in found]
if missing:
    # A branch no configuration can reach is either dead code or a fixture set that cannot test it.
    # Either way it must not pass silently.
    print("FAIL: no configuration exercises %s" % ", ".join(missing))
    sys.exit(1)

keep = []
seen = set()
for code in sorted(hour_codes):                  # two fixtures per branch, from different days
    for idx in found[code]:
        if idx in seen:
            continue
        seen.add(idx)
        keep.append(idx)
        if sum(1 for i in keep if code in [e["code"] for e in allrows[i]["events"]]) >= 2:
            break
# then a deterministic spread across everything else, so the set is not only edge cases
step = max(1, len(allrows) // 240)
for idx in range(0, len(allrows), step):
    if idx not in seen:
        seen.add(idx)
        keep.append(idx)

tapes = [allrows[i] for i in sorted(keep)]
out = os.path.join(DEMO, "ticker_cases.json")
json.dump({"generated_by": "INTAKE-ARBITER/demo/gen_ticker_cases.py",
           "formatter": formatter, "tapes": tapes,
           "searched_hour_tapes": len(allrows),
           "branch_coverage": {c: len(found[c]) for c in sorted(found)}},
          open(out, "w", encoding="utf-8"), allow_nan=False)
print("wrote %s: %d formatter values, %d tapes chosen from %d searched, all %d hour branches covered"
      % (out, len(formatter), len(tapes), len(allrows), len(hour_codes)))
