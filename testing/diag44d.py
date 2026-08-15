import numpy as np
import test_n44_adaptive_commit as m

err_pool, meta = m.load_dir_errors()
table, dirs = m.build_direction_table()
allr = table.ravel()
thr = float(np.percentile(allr, 75))
last = m.HORIZON_H - m.LEAD_H

train = m.make_days(table, err_pool, 4000, m.SEED + 1)
test = m.make_days(table, err_pool, 4000, m.SEED + 2)
dp = m.fit_dp(train, thr, m.CAPACITY_RISE, last)
_, dp_commits = m.run_adaptive(test, thr, dp)
_, adv_commits = m.run_fixed(test, 3, 0.0, thr)


def breakdown(commits, days):
    stage_total, exc_total, n_commit, n_breach = 0.0, 0.0, 0, 0
    for c, d in zip(commits, days):
        if c is None:
            breach = d["truth"] > thr
            exc_total += m.C_EXCURSION if breach else 0.0
            n_breach += breach
        else:
            online_t = c + m.LEAD_H
            hours_run = max(0, m.HORIZON_H - online_t + 1)
            stage_total += m.C_STAGE_FIXED + hours_run * m.C_STAGE_HR
            n_commit += 1
            helped = online_t <= d["peak_h"]
            eff_thr = thr + (m.CAPACITY_RISE if helped else 0.0)
            breach = d["truth"] > eff_thr
            exc_total += m.C_EXCURSION if breach else 0.0
            n_breach += breach
    n = len(days)
    print("   n_commit=%d/%d (%.1f%%)  mean_stage=%.4f  mean_excursion=%.4f  total=%.4f  n_breach=%d (%.1f%%)"
          % (n_commit, n, 100 * n_commit / n, stage_total / n, exc_total / n,
             (stage_total + exc_total) / n, n_breach, 100 * n_breach / n))


print("ADAPTIVE:")
breakdown(dp_commits, test)
print("FIXED t=3 margin=0:")
breakdown(adv_commits, test)
print("NEVER COMMIT (reference):")
breakdown([None] * len(test), test)

# what does the DP's OWN value function predict at hour 0, vs what actually happens?
edges = dp["edges"]
V0_bins = [m._to_bin(d["obs"][0]["p90"], edges) for d in test]
print("\nhour-0 bin distribution on TEST:", np.bincount(V0_bins, minlength=m.N_BINS).tolist())
