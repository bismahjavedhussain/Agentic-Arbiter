# -*- coding: utf-8 -*-
"""Build the React app and put it where the deployment actually serves it. One command.

🔴 WHY THIS EXISTS, AND THE MISTAKE IT PREVENTS. The deployed site serves
AGENTIC-ARBITER/demo/app/, which is the BUILT bundle and is committed. The source is
AGENTIC-ARBITER/app/, and app/dist/ is gitignored. The Dockerfile installs Python dependencies and
nothing else: it does not run npm, so it cannot build the app.

Which means editing app/src, committing and pushing changes NOTHING a visitor sees. Render rebuilds
faithfully, deploys the same pre-built bundle it had before, reports success, and the change is
invisible. That is the worst kind of failure: everything green, nothing different.

So: run this before committing a front-end change. It builds, copies, and records a hash of the source
it was built from, which testing/verify_shipped_app_is_current.py then uses to fail the build if the
bundle is ever stale again.

    python tools/build_app.py

WHY THE BUNDLE IS COMMITTED AT ALL, rather than built in the image. Adding Node to the image means a
second toolchain, a second lockfile to trust, and about 138 MB of node_modules resolved at deploy time
on a 0.1 CPU instance with a 500 minute monthly build budget. The bundle is 1.9 MB. Committing it is
the cheaper and more reproducible trade, and it keeps the single-file page's promise intact: what ships
is files, with no install step.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "AGENTIC-ARBITER", "app")
DIST = os.path.join(APP, "dist")
SHIP = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "app")
STAMP = os.path.join(SHIP, "_source.json")

# Everything whose change should produce a different bundle. package-lock is included because a
# dependency bump changes the output without touching a single line of src.
SOURCE_PARTS = [
    ("dir", os.path.join(APP, "src")),
    ("file", os.path.join(APP, "index.html")),
    ("file", os.path.join(APP, "package.json")),
    ("file", os.path.join(APP, "package-lock.json")),
    ("file", os.path.join(APP, "vite.config.ts")),
    ("file", os.path.join(APP, "tsconfig.json")),
    ("file", os.path.join(APP, "tsconfig.app.json")),
    ("file", os.path.join(APP, "tsconfig.node.json")),
]


def source_hash():
    """A stable SHA-256 over every input that can change the bundle.

    Sorted paths and relative names, so it does not change with the checkout location. Missing
    optional files are recorded as absent rather than skipped, because a file appearing later is
    itself a change.
    """
    h = hashlib.sha256()
    files = []
    for kind, p in SOURCE_PARTS:
        if kind == "file":
            files.append(p)
        else:
            for r, _d, fs in os.walk(p):
                for f in sorted(fs):
                    files.append(os.path.join(r, f))
    for p in sorted(files):
        rel = os.path.relpath(p, APP).replace(os.sep, "/")
        h.update(rel.encode("utf-8"))
        if os.path.isfile(p):
            h.update(b"\x01")
            h.update(io.open(p, "rb").read())
        else:
            h.update(b"\x00")
    return h.hexdigest(), len(files)


def main():
    if not os.path.isdir(APP):
        raise SystemExit("!! no app directory at %s" % APP)

    before, nfiles = source_hash()
    print("source: %d file(s), sha256 %s" % (nfiles, before[:16]))

    print("building...")
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise SystemExit("!! npx not found on PATH. Install Node, then run npm ci in "
                         "AGENTIC-ARBITER/app.")
    r = subprocess.run([npx, "vite", "build"], cwd=APP, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stdout or "")[-1500:])
        print((r.stderr or "")[-1500:])
        raise SystemExit("!! vite build failed, exit %d. Nothing was copied." % r.returncode)
    for line in (r.stdout or "").strip().split("\n")[-6:]:
        if line.strip():
            print("   %s" % line.strip()[:110])

    if not os.path.isfile(os.path.join(DIST, "index.html")):
        raise SystemExit("!! build reported success but dist/index.html is missing")

    # Replace the shipped copy wholesale. Vite's asset filenames carry content hashes, so copying
    # over the top would accumulate every old bundle forever.
    if os.path.isdir(SHIP):
        for r_, d_, fs in os.walk(SHIP, topdown=False):
            for f in fs:
                os.remove(os.path.join(r_, f))
            for d in d_:
                os.rmdir(os.path.join(r_, d))
    else:
        os.makedirs(SHIP)

    copied, mb = 0, 0
    for r_, _d, fs in os.walk(DIST):
        for f in fs:
            # Sourcemaps are 3.6 MB and buy a reader on a host nothing.
            if f.endswith(".map"):
                continue
            src = os.path.join(r_, f)
            dst = os.path.join(SHIP, os.path.relpath(src, DIST))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
            mb += os.path.getsize(dst)
    print("copied %d file(s), %.1f MB into AGENTIC-ARBITER/demo/app/" % (copied, mb / 1e6))

    after, _ = source_hash()
    if after != before:
        print("!! the source changed while building. Re-run before committing.")
    io.open(STAMP, "w", encoding="utf-8", newline="\n").write(json.dumps({
        "_what": ("SHA-256 of the app source this bundle was built from. "
                  "testing/verify_shipped_app_is_current.py recomputes it and fails if the shipped "
                  "bundle is stale, because the Dockerfile does not build the app and a stale bundle "
                  "deploys silently."),
        "built_by": "tools/build_app.py",
        "source_sha256": after,
        "source_files": nfiles,
    }, indent=2) + "\n")
    print("stamped demo/app/_source.json")
    print()
    print("Now commit AGENTIC-ARBITER/demo/app/ along with your source change, or the deployed site")
    print("will keep serving the previous bundle and report success doing it.")


if __name__ == "__main__":
    main()
