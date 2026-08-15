"""Is the DP's cost model consistent with day_cost()? A clairvoyant policy must be UNBEATABLE.

If a policy that KNOWS each day's realised outcome in advance, and simply picks the cheapest
action available, does NOT beat the fixed-hour rule, then the fixed rule is exploiting something
the DP's action space cannot express -- i.e. the two are not being scored on the same problem, and
the bug is in the cost model / action space, not in any policy.
"""
import numpy as np
import test_n44_adaptive_commit as m

err_pool, meta = m.load_dir_errors()
table, dirs = m.build_direction_table()
allr = table.ravel()
thr = float(np.percentile(allr, 75))
last = m.HORIZON_H - m.LEAD_H

test = m.make_days(table, err_pool, 4000, m.SEED + 2)

# 1. CLAIRVOYANT: per day, choose the genuinely cheapest option (incl. never-commit).
clair, clair_choice = [], []
for d in test:
    opts = [(m.day_cost(t, d, thr), t) for t in range(last + 1)]
    opts.append((m.day_cost(None, d, thr), None))
    c, choice = min(opts, key=lambda x: x[0])
    clair.append(c)
    clair_choice.append(choice)
clair = np.array(clair)

# 2. the tuned fixed rule
adv_cost, adv_commits = m.run_fixed(test, 3, 0.0, thr)

# 3. best single fixed hour, unconditional
print("CLAIRVOYANT (knows the outcome, picks cheapest): %.4f" % clair.mean())
print("tuned fixed hour-3 + margin 0               : %.4f" % adv_cost.mean())
print()
if clair.mean() > adv_cost.mean():
    print("*** IMPOSSIBLE RESULT: clairvoyant is WORSE than a fixed rule.")
    print("    The fixed rule must be reachable in the action space; it is not.")
else:
    print("clairvoyant correctly beats the fixed rule (gap %.4f) -- cost model is consistent,"
          % (adv_cost.mean() - clair.mean()))
    print("so the action space is fine and the failure is in the POLICIES, not the model.")
print()

import collections
print("clairvoyant's chosen action histogram:",
      dict(sorted(collections.Counter(clair_choice).items(),
                  key=lambda x: (x[0] is None, x[0]))))
print()

# Critical check: what does the fixed rule do that clairvoyant-per-day cannot?
# Compare on the subset where they differ.
diff = [(i, adv_commits[i], clair_choice[i]) for i in range(len(test))
        if adv_commits[i] != clair_choice[i]]
print("days where fixed rule and clairvoyant differ: %d / %d" % (len(diff), len(test)))
worse = [i for i, a, c in diff if m.day_cost(a, test[i], thr) < m.day_cost(c, test[i], thr)]
print("...of which the FIXED rule is strictly cheaper than clairvoyant's pick: %d" % len(worse))
if worse:
    i = worse[0]
    d = test[i]
    print("   example day %d: fixed picks t=%s (cost %.3f), clairvoyant picked t=%s (cost %.3f)"
          % (i, adv_commits[i], m.day_cost(adv_commits[i], d, thr),
             clair_choice[i], m.day_cost(clair_choice[i], d, thr)))
    print("   truth=%.4f peak_h=%d thr=%.4f" % (d["truth"], d["peak_h"], thr))
