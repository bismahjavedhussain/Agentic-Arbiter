"""Why does every learned policy lose? Because the signal cannot support selective commitment.

Clairvoyant says: never-commit is optimal on 84% of days. So the entire value of any policy lies
in correctly identifying the ~16% of days where committing pays. That requires the observable
(p90) to separate those days. Test whether it can, at the hour that matters.
"""
import numpy as np
import test_n44_adaptive_commit as m

err_pool, meta = m.load_dir_errors()
table, dirs = m.build_direction_table()
allr = table.ravel()
thr = float(np.percentile(allr, 75))
last = m.HORIZON_H - m.LEAD_H
test = m.make_days(table, err_pool, 4000, m.SEED + 2)

# label: is committing at the BEST hour genuinely better than never committing?
worth_it, best_t = [], []
for d in test:
    never = m.day_cost(None, d, thr)
    opts = [(m.day_cost(t, d, thr), t) for t in range(last + 1)]
    c, t = min(opts, key=lambda x: x[0])
    worth_it.append(c < never)
    best_t.append(t if c < never else None)
worth_it = np.array(worth_it)
print("days where committing (at its best hour) beats never-committing: %d / %d (%.1f%%)"
      % (worth_it.sum(), len(test), 100 * worth_it.mean()))
print()

# How well does p90 at each hour separate 'worth committing' from 'not'?
def auc(scores, labels):
    s = np.asarray(scores, float); y = np.asarray(labels, bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0: return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float); ranks[order] = np.arange(1, len(s) + 1)
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt)); np.add.at(sums, inv, ranks)
    ranks = (sums / cnt)[inv]
    return (ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg)

print("AUC of p90(t) for predicting 'is committing worth it at all':")
for t in range(last + 1):
    p = [d["obs"][t]["p90"] for d in test]
    a = auc(p, worth_it)
    print("   t=%2d (lead %2d h)  AUC=%.4f" % (t, test[0]["obs"][t]["lead"], a))
print()

# The economics: how big is the prize vs the penalty for a false positive?
gains, losses = [], []
for d, w in zip(test, worth_it):
    never = m.day_cost(None, d, thr)
    opts = [(m.day_cost(t, d, thr), t) for t in range(last + 1)]
    c, t = min(opts, key=lambda x: x[0])
    if w:
        gains.append(never - c)
    else:
        losses.append(c - never)
print("when committing IS worth it: mean gain  = %.3f (n=%d)" % (np.mean(gains), len(gains)))
print("when it is NOT worth it    : mean loss  = %.3f (n=%d) if you commit anyway"
      % (np.mean(losses), len(losses)))
print()
base = worth_it.mean()
print("break-even precision needed: a commit must be right >= %.1f%% of the time to pay off"
      % (100 * np.mean(losses) / (np.mean(gains) + np.mean(losses))))
print("base rate of 'worth it' days: %.1f%%" % (100 * base))
