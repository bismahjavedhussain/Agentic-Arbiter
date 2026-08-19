/* CROSS-LANGUAGE consistency for the conformal arithmetic: does the browser's copy of
   src/conformal.py give the same answers?

   The "how the bound is built" panel does not display shipped numbers -- it DERIVES them, live, so
   that moving alpha or n shows the arithmetic changing. That puts the finite-sample quantile in two
   languages, which is the duplicate-code-path risk this project has been bitten by repeatedly
   (gotcha #12), and here the duplicated quantity decides how wide a SAFETY margin is.

   Equality is demanded EXACTLY, not to a tolerance. `ceil((n+1)*(1-alpha))` and a sort-plus-index
   are identical IEEE-754 operations in both languages, so any difference is a real divergence rather
   than float noise -- and the fixture grid deliberately walks n across every 1/alpha boundary, which
   is the only place the ceil could plausibly land on the other side.

   Run:  node verify_browser_conformal.js
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

let CASES;
try {
  CASES = JSON.parse(fs.readFileSync(path + '/conformal_cases.json', 'utf8'));
} catch (e) {
  console.log('conformal_cases.json missing -- run `python gen_conformal_cases.py` first');
  process.exit(1);
}

const mod = new Function([
  extract('cfQuantileIndex'), extract('cfAttainable'), extract('cfMinN'), extract('cfSplit'),
  'return {cfQuantileIndex, cfAttainable, cfMinN, cfSplit};'
].join('\n'))();

let bad = 0, checked = 0;
const fail = (what, py, js) => {
  bad++;
  if (bad <= 8) console.log('  ' + what + '   python ' + JSON.stringify(py)
    + '   browser ' + JSON.stringify(js));
};

/* ---- 1. the (n, alpha) grid ---------------------------------------------------------------- */
for (const c of CASES.grid) {
  checked++;
  const ki = mod.cfQuantileIndex(c.n, c.alpha);
  if (ki.k !== c.k) fail('k       n=' + c.n + ' a=' + c.alpha, c.k, ki.k);
  else if (ki.clamped !== c.clamped) fail('clamp   n=' + c.n + ' a=' + c.alpha, c.clamped, ki.clamped);
  else if (mod.cfAttainable(c.n) !== c.ceiling)
    fail('ceiling n=' + c.n, c.ceiling, mod.cfAttainable(c.n));
  else if (mod.cfMinN(c.alpha) !== c.min_n) fail('min_n   a=' + c.alpha, c.min_n, mod.cfMinN(c.alpha));
}
console.log('(n, alpha) grid points compared : ' + CASES.grid.length);

/* ---- 2. residual arrays through split_conformal -------------------------------------------- */
let nanCases = 0;
for (const c of CASES.residuals) {
  checked++;
  if (c.res.some(x => x === null)) nanCases++;
  const s = mod.cfSplit(c.res, c.alpha);
  if (s.n !== c.n) fail('split n', c.n, s.n);
  else if (s.k !== c.k) fail('split k (n=' + c.n + ')', c.k, s.k);
  else if (s.clamped !== c.clamped) fail('split clamped', c.clamped, s.clamped);
  else if (s.ceiling !== c.ceiling) fail('split ceiling', c.ceiling, s.ceiling);
  else if (c.q === null ? !Number.isNaN(s.q) : s.q !== c.q) fail('split q (n=' + c.n + ')', c.q, s.q);
}
console.log('residual arrays compared       : ' + CASES.residuals.length
  + '  (' + nanCases + ' containing NaN, which must be dropped not sorted)');

/* ---- 3. every bound the artefacts actually ship -------------------------------------------- */
for (const c of CASES.real) {
  checked++;
  const ki = mod.cfQuantileIndex(c.n, c.alpha);
  if (ki.k !== c.k) fail('REAL k   ' + c.label, c.k, ki.k);
  else if (ki.clamped !== c.clamped) fail('REAL clamp ' + c.label, c.clamped, ki.clamped);
  else if (mod.cfAttainable(c.n) !== c.ceiling)
    fail('REAL ceiling ' + c.label, c.ceiling, mod.cfAttainable(c.n));
  if (c.res) {
    const s = mod.cfSplit(c.res, c.alpha);
    if (s.q !== c.q) fail('REAL q   ' + c.label, c.q, s.q);
  }
}
console.log('real shipped bounds reproduced : ' + CASES.real.length);
console.log('assertions made                : ' + checked);
console.log('mismatches                     : ' + bad);
console.log(bad === 0
  ? 'PASS -- the browser derives the conformal quantile exactly as src/conformal.py does'
  : 'FAIL -- the panel would show a margin the agent did not compute');
process.exit(bad === 0 ? 0 : 1);
