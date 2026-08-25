# -*- coding: utf-8 -*-
"""Driver for N-26: runs `collect` once a day until 18 Aug, then reports. FREE except the calls.

Fires at 08:30 UTC daily = 13:30 on this machine's clock = 04:30 site-local, which puts the
14:00-16:00 site-local target window about 9.5 h ahead -- comfortably inside the confirmed 12 h
horizon and matching the lead N-25 used, so every day's pair is directly comparable.

Robustness: `collect` is idempotent and does only what is due, so nothing breaks if this process
dies, the machine sleeps, or a day is skipped. Losing a day costs one day-pair, not correctness --
the report scores whatever complete pairs exist. If this driver is not running, the manual backstop
is simply:

    python test_n26_coverage.py collect

run once on any day, any time before the site window has started (before ~23:00 on this clock).
"""
import json, os, subprocess, sys, time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "results", "n26_driver.log")
SLOT_UTC_H, SLOT_UTC_M = 8, 30
# DEADLINE EXTENDED 2026-08-25. It read 2026-08-19, which had passed -- so the driver exited
# immediately and no pair had been collected since the vendor outage began on the 18th.
# Four days were lost to that outage (08-18 zero tiles, 08-19 and 08-21 completed-but-never-
# populated, 08-20 failed), and the cause turned out to be a client-side classifier bug, fixed
# today. The bound needs 9 calibration days and holds 4, so 6 more pairs are required and one pair
# is one elapsed day: this runs to 2026-09-02, which is 8 slots for 6 needed pairs -- two spare, so
# a single missed or refused day does not cost the target.
# ONE RUN A DAY IS ENOUGH FOR BOTH LEGS. `collect` does only what is due, so the 08:30 UTC slot
# fetches the previous day's OUTCOME (its window has long since elapsed) and the new day's FORECAST
# in the same run, and costs nothing for a leg already on disk.
DEADLINE = datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc)


def log(msg):
    line = "%s  %s" % (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(mode):
    r = subprocess.run([sys.executable, os.path.join(HERE, "test_n26_coverage.py"), mode],
                       cwd=HERE, capture_output=True, text=True)
    tail = "\n".join(l for l in r.stdout.splitlines() if l.strip())[-2500:]
    log("%s rc=%d\n%s" % (mode, r.returncode, tail))
    return r.returncode


def next_slot(now):
    s = now.replace(hour=SLOT_UTC_H, minute=SLOT_UTC_M, second=0, microsecond=0)
    return s if s > now else s + timedelta(days=1)


def main():
    log("driver started; daily slot %02d:%02d UTC until %s"
        % (SLOT_UTC_H, SLOT_UTC_M, DEADLINE.date()))
    while datetime.now(timezone.utc) < DEADLINE:
        nxt = next_slot(datetime.now(timezone.utc))
        if nxt >= DEADLINE:
            break
        wait = (nxt - datetime.now(timezone.utc)).total_seconds() + 30
        log("next collect %s UTC -- sleeping %.1f h" % (nxt.strftime("%m-%d %H:%M"), wait / 3600.0))
        while wait > 0:                      # sleep in chunks so a suspend/resume self-corrects
            time.sleep(min(wait, 1800))
            wait = (nxt - datetime.now(timezone.utc)).total_seconds() + 30
        run("collect")
        time.sleep(10)
        run("report")                        # harmless before enough pairs exist; shows progress
    log("deadline reached -- final report")
    return run("report")


if __name__ == "__main__":
    sys.exit(main())
