import numpy as np, sys
import test_n44_adaptive_commit as m

err_pool, meta = m.load_dir_errors()
table, dirs = m.build_direction_table()
allr = table.ravel()
thr = float(np.percentile(allr, 75))
last = m.HORIZON_H - m.LEAD_H

train = m.make_days(table, err_pool, 4000, m.SEED + 1)
test = m.make_days(table, err_pool, 4000, m.SEED + 2)

dp = m.fit_dp(train, thr, m.CAPACITY_RISE, last)
edges, ACT = dp["edges"], dp["ACT"]
print("bin edges:", np.round(edges, 4))
print()
print("ACT table (True = commit), rows=hour, cols=bin 0..9:")
for t in range(last + 1):
    print(" t=%2d  " % t, ACT[t].astype(int))
print()

N_BINS = m.N_BINS
n_no = np.zeros((last + 1, N_BINS))
k_no = np.zeros((last + 1, N_BINS))
k_yes = np.zeros((last + 1, N_BINS))
for d in train:
    bno = d["truth"] > thr
    byes = d["truth"] > thr + m.CAPACITY_RISE
    for t in range(last + 1):
        b = m._to_bin(d["obs"][t]["p90"], edges)
        n_no[t, b] += 1
        k_no[t, b] += bno
        k_yes[t, b] += byes
print("n_no (sample count per t,bin) -- min/max:", n_no.min(), n_no.max())
print("per-hour totals:", n_no.sum(axis=1))
print()
print("p_breach_no per (t,bin):")
with np.errstate(invalid="ignore", divide="ignore"):
    pb = np.where(n_no > 0, k_no / np.maximum(n_no, 1), np.nan)
for t in range(last + 1):
    print(" t=%2d " % t, np.round(pb[t], 3))

dp_cost, dp_commits = m.run_adaptive(test, thr, dp)
adv_cost, adv_commits = m.run_fixed(test, 3, 0.0, thr)
print()
print("adaptive mean cost:", dp_cost.mean())
print("fixed t=3 margin=0 mean cost:", adv_cost.mean())
import collections
print("adaptive commit-hour histogram:",
      dict(sorted(collections.Counter(dp_commits).items(), key=lambda x: (x[0] is None, x[0]))))
