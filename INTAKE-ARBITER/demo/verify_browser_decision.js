/* END-TO-END consistency: does the BROWSER reproduce the PYTHON agent's actual decisions?

   verify_browser_agent.js checks only the dynamic program. That is not enough: the DP can agree
   perfectly while the BOUND fed into it differs, and then the page shows decisions the agent never
   made. This test drives the shipped `decide()` -- extracted from index.html, not copied -- and
   compares the resulting hour-by-hour mode string against the rows `agent.py` itself wrote into
   scenarios.json for the same configuration.

   It caught a real one: when the plume-uncertainty term was added to the Python bound, the browser
   was still computing a bound without it, so every decision silently diverged.

   Run:  node verify_browser_decision.js
*/
const fs = require('fs');
const path = __dirname;
const html = fs.readFileSync(path + '/index.html', 'utf8');

function extract(name) {
  const i = html.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('function ' + name + ' not found in index.html');
  let depth = 0, started = false, j = i;
  for (; j < html.length; j++) {
    if (html[j] === '{') { depth++; started = true; }
    else if (html[j] === '}') { depth--; if (started && depth === 0) { j++; break; } }
  }
  return html.slice(i, j);
}

const T = JSON.parse(fs.readFileSync(path + '/trace.json', 'utf8'));
const SC = JSON.parse(fs.readFileSync(path + '/scenarios.json', 'utf8'));
const col = {};
SC.columns.forEach((c, i) => col[c] = i);

// stub the two browser-only helpers decide() reaches for
let CFG = {};
const src = [
  'const MODE_FREE=1, MODE_MECH=0;',
  'function $(sel){ return {value: String(CFG[sel.slice(1)])}; }',
  // decide() builds a human-readable label for the level term, and that label formats numbers.
  // Extracted rather than reimplemented, for the same reason the functions under test are.
  html.slice(html.indexOf('const fmt ='), html.indexOf('\n', html.indexOf('const fmt ='))),
  extract('H0'), extract('cfg'), extract('plan'), extract('reactive'), extract('decide'),
  'return {decide, setCfg:(c)=>{CFG=c;}};'
].join('\n');
const mod = new Function('T', 'CFG', src)(T, CFG);

/* Shipped rows the browser can reproduce: BOTH bank placements, BOTH anchor settings, every
   notice period x limit x budget x dwell x skill at the sourced dew-point limit.

   THIS FILTER USED TO SAY `r[col.anchor] === 'sensor'`, and that one clause hid a real defect for
   as long as the test has existed. `decide()` had improvised its own unanchored level term -- one
   fixed worst-magnitude offset, no conformal margin -- and disagreed with the agent on 2,588 of
   8,064 unanchored configurations, 32.1 %. A test that excludes a code path reports PASS for it.
   It was also restricted to the `longest` bank, so the refusal path was never compared either. */
const want = SC.rows.filter(r =>
  r[col.dewpoint_limit_c] === 15 &&
  r[col.aq_limit_idx] === null);

let checked = 0, bad = 0;
const seen = new Set();
const byAnchor = {};
for (const r of want) {
  const key = [r[col.case], r[col.bank_mode], r[col.anchor], r[col.offset_day], r[col.notice_h],
               r[col.limit_c], r[col.switch_budget], r[col.min_dwell_h],
               r[col.forecast_skill]].join('|');
  if (seen.has(key)) continue;
  seen.add(key);
  const c = {
    c_case: r[col.case], c_limit: r[col.limit_c], c_notice: r[col.notice_h],
    c_anchor: r[col.anchor], c_skill: r[col.forecast_skill], c_bank: r[col.bank_mode],
    c_offday: r[col.offset_day],
    c_budget: r[col.switch_budget], c_dwell: r[col.min_dwell_h],
    c_wb: 15, c_aq: 'off', c_img: 'site_aerial.png'
  };
  byAnchor[r[col.anchor]] = (byAnchor[r[col.anchor]] || 0) + 1;
  mod.setCfg(c);
  let R;
  try { R = mod.decide(); } catch (e) {
    if (bad < 3) console.log('  THREW  ' + key + '  ' + e.message);
    bad++; checked++; continue;
  }
  const js = R.A.modes.join('');
  const py = r[col.agent_modes];
  checked++;
  if (js !== py) {
    bad++;
    if (bad <= 4) {
      console.log('  MISMATCH ' + key);
      console.log('     python ' + py);
      console.log('     browser ' + js);
      console.log('     free hours: python ' + r[col.agent_free_h] + ', browser ' +
                  R.A.modes.filter(x => x === 1).length);
    }
  }
}
console.log('configurations compared : ' + checked);
console.log('   by anchor            : ' + JSON.stringify(byAnchor));
console.log('mismatches              : ' + bad);
// A path with zero rows compared is a path this test says nothing about. Assert coverage of both,
// so removing the offsets from the trace cannot silently shrink the test back to where it was.
if (!byAnchor.sensor || !byAnchor.none) {
  console.log('FAIL -- one of the two anchor settings was not compared at all');
  process.exit(1);
}
console.log(bad === 0
  ? 'PASS -- the browser reproduces the agent\'s decisions hour for hour, bound included'
  : 'FAIL -- the page would display decisions the agent did not make');
process.exit(bad === 0 ? 0 : 1);
