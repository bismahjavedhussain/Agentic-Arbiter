/* CROSS-LANGUAGE consistency for the reasoning tape: does the BROWSER produce the same sentences,
   character for character, as src/ticker.py?

   This test is stricter than the other three, and it can be, because of how the tape is built: the
   browser owns no phrases of its own. Every sentence comes from `ticker.json`'s `templates`, written
   once in Python. So there is nothing to compare "approximately" -- either the two renderers agree
   exactly or one of them is wrong.

   What is genuinely duplicated, and therefore what this actually tests:
     1. THE FORMATTER. `tkFormat` in index.html mirrors `fmt_value` in ticker.py -- four specs, and
        the awkward corners are real: negative zero renders "-0.0000" in Python and "0.0000" from
        toFixed, and Python's round-half-even can differ from toFixed's round-half-away-from-zero on
        an exact tie. Both are checked here on the real payloads rather than reasoned about.
     2. THE STAGE LOGIC. `tickerFor` mirrors `hour_stream()`: which branch fires for a calm hour, a
        refused hour, a hold versus a mode change, a covered versus a missed bound.

   Run:  node verify_browser_ticker.js
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
const TK = JSON.parse(fs.readFileSync(path + '/ticker.json', 'utf8'));
let CASES;
try {
  CASES = JSON.parse(fs.readFileSync(path + '/ticker_cases.json', 'utf8'));
} catch (e) {
  console.log('ticker_cases.json missing -- run `python gen_ticker_cases.py` first');
  process.exit(1);
}

let CFG = {};
const src = [
  'const MODE_FREE=1, MODE_MECH=0;',
  'function $(sel){ return {value: String(CFG[sel.slice(1)])}; }',
  html.slice(html.indexOf('const fmt ='), html.indexOf('\n', html.indexOf('const fmt ='))),
  extract('H0'), extract('cfg'), extract('plan'), extract('reactive'), extract('decide'),
  extract('tkFormat'), extract('tkFixed'), extract('tkRender'), extract('tkEvent'),
  extract('tickerFor'),
  'return {decide, tickerFor, tkFormat, setCfg:(c)=>{CFG=c;}};'
].join('\n');
const mod = new Function('T', 'TK', 'CFG', src)(T, TK, CFG);

/* ---- part 1: the formatter, on the awkward values, before any tape is built ---------------- */
let fbad = 0, fchecked = 0;
for (const [v, spec, want] of CASES.formatter) {
  fchecked++;
  let got;
  try { got = mod.tkFormat(v, spec); } catch (e) { got = 'THREW: ' + e.message; }
  if (got !== want) {
    fbad++;
    if (fbad <= 6) console.log('  FORMAT  (' + JSON.stringify(v) + ', "' + spec + '")  python "'
      + want + '"  browser "' + got + '"');
  }
}
console.log('formatter values compared : ' + fchecked + ',  mismatches ' + fbad);

/* ---- part 2: whole tapes, sentence for sentence -------------------------------------------- */
let checked = 0, bad = 0, events = 0;
const branchesSeen = new Set();
for (const c of CASES.tapes) {
  mod.setCfg(c.browser_cfg);
  let R;
  try { R = mod.decide(); } catch (e) {
    console.log('  decide THREW for ' + JSON.stringify(c.browser_cfg) + ': ' + e.message);
    bad++; checked++; continue;
  }
  if (!R) { console.log('  decide returned null for ' + JSON.stringify(c.browser_cfg)); bad++; checked++; continue; }
  let js;
  try { js = mod.tickerFor(R, c.hour_index); } catch (e) {
    console.log('  tickerFor THREW at h' + c.hour_index + ': ' + e.message);
    bad++; checked++; continue;
  }
  checked++;
  if (js.length !== c.events.length) {
    bad++;
    if (bad <= 4) console.log('  LENGTH  ' + c.label + '  python ' + c.events.length
      + ' events, browser ' + js.length);
    continue;
  }
  for (let i = 0; i < js.length; i++) {
    events++;
    branchesSeen.add(js[i].code);
    if (js[i].code !== c.events[i].code) {
      bad++;
      if (bad <= 4) console.log('  BRANCH  ' + c.label + ' event ' + i + '  python '
        + c.events[i].code + '  browser ' + js[i].code);
      break;
    }
    if (js[i].text !== c.events[i].text) {
      bad++;
      if (bad <= 4) {
        console.log('  TEXT    ' + c.label + ' ' + c.events[i].code);
        console.log('     python  ' + c.events[i].text);
        console.log('     browser ' + js[i].text);
      }
      break;
    }
  }
}
console.log('tapes compared            : ' + checked);
console.log('event sentences compared  : ' + events);
console.log('distinct branches exercised: ' + branchesSeen.size + ' of '
  + Object.keys(TK.templates).filter(k => k.startsWith('hour.')).length + ' hour templates');
console.log('mismatches                : ' + (bad + fbad));

/* Every hour-template branch must actually fire somewhere in the fixture set. A branch that is
   never exercised is a branch this test says nothing about -- the same hole that let
   verify_browser_decision.js report PASS while the unanchored path was 32 % wrong. */
const hourCodes = Object.keys(TK.templates).filter(k => k.startsWith('hour.'));
const unexercised = hourCodes.filter(k => !branchesSeen.has(k));
if (unexercised.length) {
  console.log('FAIL -- these hour templates were never rendered by any fixture: '
    + unexercised.join(', '));
  process.exit(1);
}
console.log((bad + fbad) === 0
  ? 'PASS -- the browser renders every stage event exactly as Python does, character for character'
  : 'FAIL -- the page would show sentences the agent did not produce');
process.exit((bad + fbad) === 0 ? 0 : 1);
