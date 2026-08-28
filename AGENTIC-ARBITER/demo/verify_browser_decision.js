/* END-TO-END consistency: does the BROWSER's agent reproduce the PYTHON agent's actual decisions?

   verify_browser_agent.js checks only the dynamic program. That is not enough: the DP can agree
   perfectly while the BOUND fed into it differs, and then the page shows decisions the agent never
   made. This test drives the shipped `decide()` and compares the resulting hour-by-hour mode string
   against the rows `agent.py` itself wrote into scenarios.json for the same configuration.

   It caught a real one: when the plume-uncertainty term was added to the Python bound, the browser
   was still computing a bound without it, so every decision silently diverged.

   🔴 2026-08-28: THIS TEST NO LONGER SCRAPES THE PAGE, AND IT NO LONGER FAKES A BROWSER.
   It used to locate `function decide(` inside index.html by string search, brace-match the body out,
   and `new Function(...)` it -- and because the agent read its configuration straight out of the DOM,
   the test also had to define a fake `$()` returning fake <select> values before it could run
   anything. That is a verification harness working around a design problem.
   The agent now lives in ../core/ as importable modules that take their inputs as arguments, so this
   file imports it. What is being tested is the same code; what has gone is the pretence of a browser.

   WHY THE CONFIG STILL GOES THROUGH cfgFromStrings(). A <select> always yields a STRING, so the page
   hands the agent `offday: "0"` and not `offday: 0`. Building the object from scenarios.json's raw
   JSON types would hand it a number instead, and a string-versus-number difference in a key the agent
   compares is a behaviour change no assertion here would catch. Same coercions, one definition.

   Run:  node verify_browser_decision.js
*/
const fs = require('fs');
const path = __dirname;

const T = JSON.parse(fs.readFileSync(path + '/trace.json', 'utf8'));
const SC = JSON.parse(fs.readFileSync(path + '/scenarios.json', 'utf8'));
const col = {};
SC.columns.forEach((c, i) => col[c] = i);

(async () => {
  // Dynamic import because this file is CommonJS: audit.py check 8 runs it as `node
  // verify_browser_decision.js` and check_dead_code scans it by that name, so the filename stays.
  const { decide } = await import('../core/agent.mjs');
  const { cfgFromStrings } = await import('../core/config.mjs');

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

    // The eleven control values this row implies, as the STRINGS a <select> would have produced.
    const raw = {
      '#c_case': r[col.case], '#c_limit': r[col.limit_c], '#c_notice': r[col.notice_h],
      '#c_anchor': r[col.anchor], '#c_skill': r[col.forecast_skill], '#c_bank': r[col.bank_mode],
      '#c_budget': r[col.switch_budget], '#c_dwell': r[col.min_dwell_h],
      '#c_offday': r[col.offset_day], '#c_wb': 15, '#c_aq': 'off'
    };
    const k = cfgFromStrings(id => {
      if (!(id in raw)) throw new Error('the config asked for an unmapped control: ' + id);
      return String(raw[id]);
    });

    byAnchor[r[col.anchor]] = (byAnchor[r[col.anchor]] || 0) + 1;
    let R;
    try { R = decide(k, T); } catch (e) {
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
})().catch(e => { console.log('FAIL -- ' + (e && e.stack || e)); process.exit(1); });
