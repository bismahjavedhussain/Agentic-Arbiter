/* Does the BROWSER's explainer agree with the PYTHON one on WHY each hour was decided?

   The decision test (verify_browser_decision.js) proves the two agree on WHAT was decided. That
   leaves the seventh stage unchecked: an explanation could name the wrong binding constraint while
   the mode itself matches, and a viewer would be told a confident, wrong reason.

   Both sides are compared per hour on `binding` -- refusal / dry-bulb / dew point / air quality /
   switch budget / minimum dwell / none. Functions are EXTRACTED from index.html, so this tests the
   code that ships.

   Run:  node verify_browser_explanation.js     (needs demo/explanations.json from explain.py)
*/
const fs = require('fs');
const p = __dirname;
const html = fs.readFileSync(p + '/index.html', 'utf8');

/* 🔴 THE PAGE IS NO LONGER SCRAPED. This used to locate `function NAME(` inside index.html by
   string search and brace-match the body out. The agent now lives in ../core/ as importable modules
   that take their inputs as arguments, so it is imported. Same code under test; what has gone is the
   string search, and with it the need to pretend to be a browser.
   `require()` of an ES module is supported from Node 22.12; this repository's checks run on v24. */

const T = JSON.parse(fs.readFileSync(p + '/trace.json', 'utf8'));
const EX = JSON.parse(fs.readFileSync(p + '/explanations.json', 'utf8'));

/* 🔴 AND THE LOCAL `fmt` STUB IS GONE, WHICH MATTERS. It returned an ASCII hyphen "-" for a null,
   while the page's real formatter returns an EN DASH. So this test has always compared explanations
   built with one formatter against a page that ships another, and a null-valued explanation would
   have differed with nothing to report it. core/explain.mjs imports the real one. */
const { decide } = require('../core/agent.mjs');
const { explainHour } = require('../core/explain.mjs');
const { cfgFromStrings } = require('../core/config.mjs');

/* THE CONFIG SHIM. The loop below hands over an object keyed by CONTROL ID minus the '#', because
   that is what the old fake `$()` consumed (`CFG[sel.slice(1)]`). cfgFromStrings() applies the page's
   own eleven coercions to it, so `offday` arrives as the string a <select> would have produced rather
   than as scenarios.json's number. Reproducing those coercions by hand here is exactly the drift the
   shared module exists to prevent. */
let K = null;
const mod = {
  setCfg: (c) => { K = cfgFromStrings(id => String(c[id.slice(1)])); },
  decide: () => decide(K, T),
  explainHour: (R, h) => explainHour(R, h)
};

let compared = 0, bad = 0;
const kinds = {};
for (const caseName of Object.keys(EX.cases)) {
  for (const blk of EX.cases[caseName]) {
    const c = blk.config;
    // only configurations the browser exposes
    if (c.aq_limit_idx !== null && c.aq_limit_idx !== 73.5) continue;
    mod.setCfg({
      c_case: caseName, c_limit: c.limit_c, c_notice: c.notice_h, c_anchor: c.anchor,
      c_skill: c.skill, c_bank: c.bank_mode, c_budget: c.switch_budget, c_dwell: c.min_dwell_h,
      c_wb: c.dewpoint_limit_c === null ? 'off' : c.dewpoint_limit_c,
      c_aq: c.aq_limit_idx === null ? 'off' : c.aq_limit_idx,
      c_img: 'site_aerial.png'
    });
    let R;
    try { R = mod.decide(); } catch (e) { bad++; compared++; continue; }
    if (!R) { bad++; compared++; continue; }
    for (let h = 0; h < blk.hours.length; h++) {
      const py = blk.hours[h];
      const js = mod.explainHour(R, h);
      compared++;
      kinds[py.binding || 'none'] = (kinds[py.binding || 'none'] || 0) + 1;
      if ((py.binding || null) !== (js.binding || null)) {
        bad++;
        if (bad <= 6) console.log('  MISMATCH ' + caseName + ' h' + h
          + ' limit=' + c.limit_c + ' bank=' + c.bank_mode + ' notice=' + c.notice_h
          + '  python="' + py.binding + '"  browser="' + js.binding + '"');
      }
      if (py.mode !== js.mode) {
        bad++;
        if (bad <= 6) console.log('  MODE MISMATCH ' + caseName + ' h' + h
          + '  python=' + py.mode + ' browser=' + js.mode);
      }
    }
  }
}
console.log('hour-explanations compared : ' + compared);
console.log('binding kinds seen         : '
  + Object.entries(kinds).map(([k, v]) => k + '=' + v).join(', '));
console.log('mismatches                 : ' + bad);
console.log(bad === 0
  ? 'PASS -- the browser and the Python agent give the SAME reason for every hour'
  : 'FAIL -- the interface would state a reason the agent did not have');
process.exit(bad === 0 ? 0 : 1);
