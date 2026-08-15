import numpy as np
import test_n44_adaptive_commit as m

err_pool, meta = m.load_dir_errors()
table, dirs = m.build_direction_table()
allr = table.ravel()
thr = float(np.percentile(allr, 75))
last = m.HORIZON_H - m.LEAD_H

for n_train, n_bins in ((4000, 10), (4000, 4), (20000, 10), (20000, 4)):
    m.N_BINS = n_bins
    train = m.make_days(table, err_pool, n_train, m.SEED + 1)
    test = m.make_days(table, err_pool, 4000, m.SEED + 2)
    dp = m.fit_dp(train, thr, m.CAPACITY_RISE, last)
    dp_cost, dp_commits = m.run_adaptive(test, thr, dp)
    adv_cost, adv_commits = m.run_fixed(test, 3, 0.0, thr)

    edges, ACT = dp["edges"], dp["ACT"]
    # per (t,bin) sample counts on TRAIN, to see how thin the high-risk bins are
    n_no = np.zeros((last + 2, n_bins))
    for d in train:
        for t in range(last + 2):
            b = m._to_bin(d["obs"][t]["p90"], edges)
            n_no[t, b] += 1
    print("n_train=%5d n_bins=%d  adaptive=%.3f  fixed_t3=%.3f  min_cell_n=%d  bin_counts_row0=%s"
          % (n_train, n_bins, dp_cost.mean(), adv_cost.mean(), int(n_no.min()),
             n_no[0].astype(int).tolist()))
