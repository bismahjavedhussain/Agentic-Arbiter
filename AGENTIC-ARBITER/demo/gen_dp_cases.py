# -*- coding: utf-8 -*-
"""Write dp_cases.json: 500 random safety patterns scored by the PYTHON agent, so that
`node verify_browser_agent.js` can check the browser's copy of the scheduler against it.

The browser re-runs the agent so that moving a control genuinely re-decides. That puts the
scheduler in two languages, which is the duplicate-code-path risk this project has been bitten by
(gotcha #12) -- and here a silent disagreement would be in a safety decision. Hence this test.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from agent import plan, reactive_incumbent          # noqa: E402

rng = np.random.default_rng(2026)
cases = []
for _ in range(500):
    H = int(rng.integers(6, 25))
    safe = rng.random(H) < rng.uniform(0.05, 0.95)
    b, d = int(rng.integers(1, 5)), int(rng.integers(1, 4))
    _, f, sw = plan(list(safe), b, d)
    _, fi, swi, over = reactive_incumbent(safe, b, d)
    cases.append({"safe": [bool(x) for x in safe], "budget": b, "dwell": d,
                  "py_free": int(f), "py_sw": int(sw),
                  "py_inc_free": int(fi), "py_inc_sw": int(swi), "py_inc_over": int(over)})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dp_cases.json")
json.dump({"cases": cases}, open(out, "w"), allow_nan=False)
print("wrote %s with %d cases from the PYTHON agent" % (out, len(cases)))
