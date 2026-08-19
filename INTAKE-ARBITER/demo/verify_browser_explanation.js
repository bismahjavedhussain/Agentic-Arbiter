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

function extract(name) {
  const i = html.indexOf('function ' + name + '(');
  if (i < 0) throw new Error('function ' + name + ' not found');
  let d = 0, started = false, j = i;
  for (; j < html.length; j++) {
    if (html[j] === '{') { d++; started = true; }
    else if (html[j] === '}') { d--; if (started && d === 0) { j++; break; } }
  }
  return html.slice(i, j);
}

const T = JSON.parse(fs.readFileSync(p + '/trace.json', 'utf8'));
const EX = JSON.parse(fs.readFileSync(p + '/explanations.json', 'utf8'));

let CFG = {};
const src = [
  'const MODE_FREE=1, MODE_MECH=0;',
  'function $(sel){ return {value: String(CFG[sel.slice(1)])}; }',
  'function fmt(v,d){ d=(d===undefined?2:d); return (v===null||v===undefined||Number.isNaN(v))?"-":(+v).toFixed(d); }',
  extract('H0'), extract('cfg'), extract('plan'), extract('reactive'),
  extract('decide'), extract('explainHour'),
  'return {decide, explainHour, setCfg:(c)=>{CFG=c;}};'
].join('\n');
const mod = new Function('T', 'CFG', src)(T, CFG);

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
