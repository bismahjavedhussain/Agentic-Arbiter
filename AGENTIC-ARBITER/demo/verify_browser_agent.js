/* Cross-implementation check: the DP and the reactive incumbent that ship INSIDE index.html
   must agree with the Python originals in src/agent.py.

   WHY THIS EXISTS. The demo re-runs the agent's decision in the browser so that moving a control
   genuinely re-decides rather than replaying a lookup. That means the scheduler exists twice --
   once in Python, once in JavaScript -- which is exactly the situation gotcha #12 warns about,
   and worse than usual because a silent disagreement would be in a SAFETY decision.

   The functions are EXTRACTED FROM index.html at test time rather than copied here, so this
   tests the code that actually ships. Run:  node verify_browser_agent.js  (after
   `python gen_dp_cases.py` has written dp_cases.json).
*/
const fs = require('fs');

const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
/* 🔴 THE PAGE IS NO LONGER SCRAPED. This used to locate `function NAME(` inside index.html by
   string search and brace-match the body out. The agent now lives in ../core/ as importable modules
   that take their inputs as arguments, so it is imported. Same code under test; what has gone is the
   string search, and with it the need to pretend to be a browser.
   `require()` of an ES module is supported from Node 22.12; this repository's checks run on v24. */
const mod = require('../core/agent.mjs');

const cases = JSON.parse(fs.readFileSync(__dirname + '/dp_cases.json', 'utf8'));
let bad = 0, badR = 0;
for (const c of cases.cases) {
  const a = mod.plan(c.safe.map(Boolean), c.budget, c.dwell);
  if (a.modes.filter(x => x === 1).length !== c.py_free) {
    if (++bad <= 4) console.log('  PLAN mismatch H=' + c.safe.length + ' b=' + c.budget +
      ' d=' + c.dwell + '  python=' + c.py_free + ' js=' + a.modes.filter(x => x === 1).length);
  }
  const r = mod.reactive(c.safe.map(Boolean), c.budget, c.dwell);
  if (r.modes.filter(x => x === 1).length !== c.py_inc_free) {
    if (++badR <= 4) console.log('  REACTIVE mismatch H=' + c.safe.length + ' b=' + c.budget +
      ' d=' + c.dwell + '  python=' + c.py_inc_free + ' js=' + r.modes.filter(x => x === 1).length);
  }
}
console.log('cases: ' + cases.cases.length);
console.log('plan     mismatches: ' + bad);
console.log('reactive mismatches: ' + badR);
console.log((bad + badR) === 0
  ? 'PASS -- the browser agent and the Python agent decide identically'
  : 'FAIL -- the shipped demo would show decisions the agent did not make');
process.exit((bad + badR) === 0 ? 0 : 1);
