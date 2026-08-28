# -*- coding: utf-8 -*-
r"""The bundle that ships must have been built from the source that is committed.

🔴 THE FAILURE THIS CATCHES IS SILENT, WHICH IS WHY IT NEEDS A GATE. The deployed site serves
AGENTIC-ARBITER/demo/app/, the built bundle, which is committed. The source is
AGENTIC-ARBITER/app/, and the Dockerfile installs Python dependencies and nothing else: there is no
Node in the image, so it cannot build the app.

So edit app/src, commit, push. Render rebuilds faithfully, deploys the bundle it already had, reports
SUCCESS, and nothing a visitor sees has changed. Every light is green and the change is invisible.
No other check in this repository would notice: audit.py reads the single-file page, the byte-identity
verifiers compare the engine against the page, and the flow check drives whatever bundle happens to be
on disk.

HOW IT WORKS. tools/build_app.py records a SHA-256 over every input that can change the bundle
(app/src, index.html, package.json, package-lock.json, vite.config.ts, the tsconfigs) into
demo/app/_source.json. This recomputes that hash from the working tree and compares. A mismatch means
the source moved after the last build.

WHY HASH THE SOURCE RATHER THAN COMPARE THE OUTPUT. Comparing outputs would mean running a build,
which needs Node, a 138 MB node_modules and about ten seconds, in a suite whose whole point is that it
runs offline with zero API calls in a predictable time. Hashing the inputs answers the same question
for nothing.

EXIT CODES
  0  the shipped bundle matches the committed source
  1  STALE: rebuild with `python tools/build_app.py` and commit demo/app/
  3  cannot tell: no bundle or no stamp. A skip, not a pass.
"""
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "AGENTIC-ARBITER", "app")
SHIP = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "app")
STAMP = os.path.join(SHIP, "_source.json")

# 🔴 THIS LIST MUST MATCH tools/build_app.py EXACTLY. If they drift, the hash is meaningless: it would
# either fail forever or never fail. Kept in both places rather than imported because testing/ and
# tools/ are separate roots and a cross-import would be the more fragile coupling.
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


print("=" * 78)
print("demo/app/ vs AGENTIC-ARBITER/app/: is the shipped bundle built from the committed source?")
print("=" * 78)

if not os.path.isfile(os.path.join(SHIP, "index.html")):
    print("   [skip] no bundle at AGENTIC-ARBITER/demo/app/.")
    print("          Build it with: python tools/build_app.py")
    print("          Skipping is not passing: the deployment serves this folder.")
    sys.exit(3)

if not os.path.isfile(STAMP):
    print("   [skip] demo/app/ exists but carries no _source.json stamp, so it cannot be checked.")
    print("          Rebuild once with: python tools/build_app.py")
    sys.exit(3)

stamp = json.loads(io.open(STAMP, encoding="utf-8").read())
want = stamp.get("source_sha256")
got, nfiles = source_hash()

print("   stamped at build : %s  (%s source files)" % (str(want)[:24], stamp.get("source_files")))
print("   source now       : %s  (%s source files)" % (got[:24], nfiles))
print()

if want == got:
    # And the bundle has to be internally coherent: index.html must reference assets that exist.
    idx = io.open(os.path.join(SHIP, "index.html"), encoding="utf-8").read()
    import re
    refs = re.findall(r'(?:src|href)="\./([^"]+)"', idx)
    missing = [r for r in refs if not os.path.isfile(os.path.join(SHIP, r))]
    if missing:
        print("   [FAIL] index.html references %d asset(s) that are not in demo/app/: %s"
              % (len(missing), ", ".join(missing[:3])))
        print()
        print("   The stamp matches but the folder is incomplete. Rebuild:")
        print("       python tools/build_app.py")
        sys.exit(1)
    print("   [ok]   the shipped bundle was built from exactly this source")
    print("   [ok]   its %d referenced asset(s) are all present" % len(refs))
    print()
    print("VERDICT: PASS. A push will deploy what the source says.")
    sys.exit(0)

print("   [FAIL] THE SHIPPED BUNDLE IS STALE.")
print()
print("   The app source has changed since demo/app/ was last built. Pushing now would deploy the")
print("   PREVIOUS interface: Render would rebuild, succeed, and serve the old bundle, with nothing")
print("   anywhere reporting a problem.")
print()
print("   Fix:")
print("       python tools/build_app.py")
print("       git add AGENTIC-ARBITER/demo/app")
print("   then commit that alongside your source change.")
sys.exit(1)
