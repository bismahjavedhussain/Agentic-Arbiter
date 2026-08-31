/* THE INCUMBENT'S HOUR-BY-HOUR SCHEDULE, FROM THE PAGE'S OWN DECISION CODE.
 *
 * Usage:  node site_report_decide.mjs <trace.json> <case> <limit> <notice> <anchor> <skill>
 *                                     <bank> <budget> <dwell> <offday> <dp> <aq>
 * Prints one JSON object on stdout.
 *
 * 🔴 WHY THIS EXISTS RATHER THAN A PYTHON REIMPLEMENTATION.
 * The report's before/after comparison needs the reactive incumbent's mode for every hour, and that
 * quantity is not in any artefact. `explanations.json` carries the AGENT's hours and only aggregate
 * incumbent counts (`incumbent_free_h`); `trace.cases.day_series` carries `incumbent_src`, which is
 * the sensor reading the incumbent acts on, not the action it takes. The schedule itself only ever
 * exists inside `decide()`.
 *
 * `decide()` is in `core/agent.mjs`, lifted byte-for-byte out of the page, and `run_all.py` step 29
 * asserts the two are still the same code. So calling it is the one way to put the incumbent in the
 * report without creating a second implementation that can drift from the product. Writing the
 * reactive controller again in Python would have meant two answers to one question and no way to
 * tell which was right, which is the shape this project has been bitten by before.
 */
import { readFileSync } from 'node:fs'
import { decide } from '../core/agent.mjs'

const a = process.argv.slice(2)
if (a.length < 12) {
  console.error('need 12 arguments: trace case limit notice anchor skill bank budget dwell offday dp aq')
  process.exit(2)
}
const [tracePath, kase, limit, notice, anchor, skill, bank, budget, dwell, offday, dp, aq] = a

const trace = JSON.parse(readFileSync(tracePath, 'utf8'))
const num = (v) => (v === 'null' || v === '' ? null : +v)

/* The field names are the page's, not the artefact's: `cfg()` in index.html builds exactly this
   object from the eleven controls, and decide() reads `k.limit` / `k.notice` / `k.bank` and so on.
   explanations.json spells the same settings `limit_c` / `notice_h` / `bank_mode`, so the caller
   translates and this file does not, to keep one mapping in one place. */
const k = {
  case: kase,
  limit: +limit,
  notice: +notice,
  anchor: anchor,
  skill: +skill,
  bank: bank,
  budget: +budget,
  dwell: +dwell,
  offday: offday === 'null' ? null : offday,
  dp: num(dp),
  aq: num(aq),
}

const R = decide(k, trace)
if (!R) {
  console.error('decide() returned null: no day_series for case ' + kase)
  process.exit(3)
}

/* Only what the report draws. Dumping the whole object would put megabytes through a pipe and
   invite the report to depend on internals it has no business reading. */
process.stdout.write(JSON.stringify({
  hours: R.ds.hours,
  agent_modes: Array.from(R.A.modes),
  incumbent_modes: Array.from(R.I.modes),
  bound: Array.from(R.ubD),
  truth: Array.from(R.truth),
  truly_safe: Array.from(R.trulySafe),
  refused: Array.from(R.refused, (x) => !!x),
  limit: R.k.limit,
  agent_free_h: R.aFree,
  incumbent_free_h: R.iFree,
  agent_breach_h: R.aBreach,
  incumbent_breach_h: R.iBreach,
  agent_refused_h: R.aRef,
  agent_switches: R.A.switches,
  incumbent_switches: R.I.switches,
}))
