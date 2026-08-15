# -*- coding: utf-8 -*-
"""Driver for N-25: sleeps until each shot is due, fires it, repeats. FREE except the shots.

Why a driver rather than polling on a timer: poll() is idempotent and safe to run at any moment,
but each run also reads the usage endpoint, so polling every 15 minutes for twelve hours would
generate ~100 pointless requests. This wakes only when something is actually due -- six times.

Robustness: if this process dies, nothing is lost. The manifest records every completed shot, and
`python test_n25_sharpen.py poll` catches up whatever is due. A shot fired late records its ACTUAL
lead, and the fit uses actual leads, so drift changes the lead SPACING without corrupting the
measurement. The only unrecoverable case is a shot whose window has already started, which poll()
detects and skips explicitly rather than recording a bogus lead.
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "results", "n25_manifest.json")
LOG = os.path.join(HERE, "results", "n25_driver.log")
MAX_RUNTIME_S = 16 * 3600
SLACK_S = 20          # fire a touch after the due instant, never before


def log(msg):
    line = "%s  %s" % (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def iso(s):
    return datetime.fromisoformat(s)


def next_due(m):
    """Earliest pending due instant, or None when everything is collected."""
    pending = [iso(s["due_utc"]) for s in m["shots"] if not s["done"]]
    if not m["outcome"].get("done"):
        pending.append(iso(m["outcome_due_utc"]))
    return min(pending) if pending else None


def main():
    t0 = time.time()
    if not os.path.exists(MANIFEST):
        log("no manifest -- run 'python test_n25_sharpen.py plan' first")
        return 2
    log("driver started")

    while time.time() - t0 < MAX_RUNTIME_S:
        m = json.load(open(MANIFEST))
        nd = next_due(m)
        if nd is None:
            log("all shots and the outcome are collected -- running report")
            r = subprocess.run([sys.executable, os.path.join(HERE, "test_n25_sharpen.py"), "report"],
                               cwd=HERE, capture_output=True, text=True)
            log("report rc=%d\n%s" % (r.returncode, r.stdout[-4000:]))
            return r.returncode

        wait = (nd - datetime.now(timezone.utc)).total_seconds() + SLACK_S
        if wait > 0:
            log("next due %s UTC -- sleeping %.1f min" % (nd.strftime("%H:%M:%S"), wait / 60.0))
            time.sleep(min(wait, MAX_RUNTIME_S))

        r = subprocess.run([sys.executable, os.path.join(HERE, "test_n25_sharpen.py"), "poll"],
                           cwd=HERE, capture_output=True, text=True)
        tail = "\n".join(l for l in r.stdout.splitlines() if l.strip())[-2500:]
        log("poll rc=%d\n%s" % (r.returncode, tail))
        if r.returncode not in (0, 2):
            log("poll returned %d -- continuing anyway; poll is idempotent" % r.returncode)
        time.sleep(5)

    log("driver hit its %d h runtime cap with work outstanding" % (MAX_RUNTIME_S // 3600))
    return 1


if __name__ == "__main__":
    sys.exit(main())
