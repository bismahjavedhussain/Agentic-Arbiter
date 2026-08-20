"""FULL-TREE + FULL-HISTORY SECRET SCAN. Run this before making the repository public.

WHY IT SCANS HISTORY AND NOT JUST THE WORKING TREE
--------------------------------------------------
A public repository publishes every commit, not the tip. Redacting a key in commit N leaves it
readable in commit N-1 forever, and `git log -p` is the first thing a scraper runs. Three
credential incidents are on record for this project (HANDOFF 12.3) and all three were caught
before the first commit -- this script is what PROVES that claim instead of asserting it.

HOW IT AVOIDS BECOMING THE LEAK ITSELF
--------------------------------------
Rule 8: the key is read ONLY through `common.load_key()`, and is never printed, echoed, logged or
written anywhere. Specifically:

  * The key is never passed as a command-line argument. `git grep -e <key>` would put it in the
    process table and, run from a shell, in the shell history. So history is scanned by streaming
    every blob through `git cat-file --batch` and searching the BYTES inside this process.
  * The key is never written to a temp pattern file for `git grep -f`, for the same reason.
  * Findings print a path, a line number and a REDACTION (`len=44 sha256=1a2b3c4d`), never the text
    that matched -- because a scan report is itself a document somebody will paste somewhere.
  * The key's identity is reported as an 8-hex SHA-256 prefix, which is how the two on-disk .env
    files were compared in the first place (HANDOFF 12.1).

EXIT STATUS
-----------
0 = clean. 1 = at least one hit somewhere git would publish (a tracked file, or any blob in
history). Untracked-but-not-ignored files are reported as WARN and do not fail the run: git will
not publish them today, but they are one `git add -A` away from being published.

USAGE
-----
    python testing/scan_secrets.py          # zero API calls, reads .env but never emits it
"""
import hashlib
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import common  # noqa: E402  -- provides load_key(); the only sanctioned reader of the key


def fp(b):
    """An 8-hex fingerprint of a secret. Never the secret."""
    if isinstance(b, str):
        b = b.encode()
    return hashlib.sha256(b).hexdigest()[:8]


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, check=True)
    return out.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- what counts as a secret
# The literal key is the only thing we KNOW is a secret here. Everything below is a SHAPE that has
# leaked credentials in other projects, kept because this repository is about to be read by
# strangers.
#
# Every assignment pattern demands a VALUE of real length. `"api_key": key` in source code is a
# variable name, not a credential, and a pattern that fires on it teaches the reader to skim the
# report -- which is exactly how a real hit gets missed. Hence the 16-character floor.
PATTERNS = [
    ("api-key assignment",
     rb"(?i)\b(?:api[-_]?key|apikey|access[-_]?token|auth[-_]?token|secret|password|passwd)\b"
     rb"""\s*[:=]\s*["']([A-Za-z0-9_\-\.]{16,})["']"""),
    ("bearer token",      rb"(?i)bearer\s+([A-Za-z0-9_\-\.=]{20,})"),
    ("openai-style key",  rb"\b(sk-[A-Za-z0-9]{20,})"),
    ("github token",
     rb"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("aws access key id", rb"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"),
    ("private key block", rb"(-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----)"),
    ("slack token",       rb"\b(xox[abprs]-[A-Za-z0-9\-]{10,})"),
]

# Placeholders that are SUPPOSED to look like credentials. Held as exact values rather than a loose
# "contains the word example" rule, so a real key sitting next to a placeholder still fires.
ALLOWED_VALUES = {
    b"your-fortyguard-api-key-here", b"your_api_key_here", b"YOUR_API_KEY_HERE",
    b"replace-me", b"xxxxxxxxxxxxxxxx", b"REDACTED", b"redacted", b"REDACTED_API_KEY",
}

SKIP_REGEX_EXT = {".png", ".jpg", ".jpeg", ".pdf", ".npy", ".npz", ".xlsx", ".zip",
                  ".woff", ".woff2", ".ttf", ".ico"}
MAX_REGEX_BYTES = 8 * 1024 * 1024       # regex only on files a human could plausibly have typed
MAX_FILE_BYTES = 64 * 1024 * 1024


def scan_bytes(data, key_forms, do_regex=True):
    """Return [(kind, line_no, redaction)]. Never returns matched text."""
    hits = []
    for label, form in key_forms:
        start = 0
        while True:
            i = data.find(form, start)
            if i < 0:
                break
            hits.append((label, data.count(b"\n", 0, i) + 1,
                         "len=%d sha256=%s" % (len(form), fp(form))))
            start = i + 1
    if not do_regex:
        return hits
    for label, pat in PATTERNS:
        for m in re.finditer(pat, data):
            val = m.group(1)
            if val in ALLOWED_VALUES or val.lower().startswith(b"your"):
                continue
            hits.append((label, data.count(b"\n", 0, m.start()) + 1,
                         "len=%d sha256=%s" % (len(val), fp(val))))
    return hits


def key_forms_for(kb):
    """The forms a leak actually takes: verbatim, url-encoded, and either half on its own."""
    forms = [
        ("THE FORTYGUARD KEY, verbatim", kb),
        ("the key, url-encoded",
         kb.replace(b"%", b"%25").replace(b"+", b"%2B").replace(b"/", b"%2F").replace(b"=", b"%3D")),
        ("the key's leading 16 chars", kb[:16]),
        ("the key's trailing 16 chars", kb[-16:]),
    ]
    # A short key would make the partial forms fire on ordinary prose. Drop the partials rather
    # than emit noise the reader learns to ignore; the verbatim form still covers the real case.
    if len(kb) < 32:
        forms = forms[:2]
    seen = set()
    return [(lbl, f) for lbl, f in forms if f and not (f in seen or seen.add(f))]


def main():
    key = common.load_key()          # rule 8: the only read, and it never leaves this process
    kb = key.encode()
    forms = key_forms_for(kb)

    print("=" * 78)
    print("SECRET SCAN -- working tree and every blob in history")
    print("=" * 78)
    print("key on disk: %d chars, sha256 prefix %s   (the value is never printed)"
          % (len(key), fp(kb)))
    print("searching for %d key forms + %d generic credential shapes"
          % (len(forms), len(PATTERNS)))
    print()

    fails, warns = [], []

    # ------------------------------------------------------------ 1. the working tree
    tracked = [p for p in git("ls-files", "-z").split("\0") if p]
    untracked = [p for p in git("ls-files", "-zo", "--exclude-standard").split("\0") if p]
    print("1. WORKING TREE -- %d tracked, %d untracked-and-not-ignored"
          % (len(tracked), len(untracked)))
    for group, paths, bucket in (("tracked", tracked, fails), ("untracked", untracked, warns)):
        for p in paths:
            full = os.path.join(ROOT, p)
            try:
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
                data = open(full, "rb").read()
            except OSError:
                continue
            ext = os.path.splitext(p)[1].lower()
            do_re = ext not in SKIP_REGEX_EXT and len(data) <= MAX_REGEX_BYTES
            for kind, line, red in scan_bytes(data, forms, do_re):
                bucket.append(("%s:%d" % (p, line), kind, red, group))

    # ------------------------------------------------------------ 2. every blob ever committed
    # `rev-list --objects --all` names every object reachable from every ref, INCLUDING blobs no
    # commit at the tip still references -- which is exactly where a redacted-later key hides.
    objs = {}
    for line in git("rev-list", "--objects", "--all").splitlines():
        sha, _, path = line.partition(" ")
        if path:
            objs.setdefault(sha, path)
    n_commits = len(git("rev-list", "--all").split())
    print("2. HISTORY -- %d commits, %d named blobs to read" % (n_commits, len(objs)))

    # cat-file --batch reads one SHA per line on stdin and writes "<sha> <type> <size>\n<bytes>\n".
    # Streaming keeps the key out of every argv while still reading the whole object database.
    #
    # THE STDIN WRITE MUST HAPPEN ON ANOTHER THREAD, and the first version of this deadlocked for
    # 27 minutes because it did not. Windows gives a subprocess pipe a ~4 KB default buffer, and
    # this repository has 769 objects = ~31 KB of SHAs. So: we block partway through writing; git
    # meanwhile emits blob content until ITS stdout buffer fills and blocks; a blocked git stops
    # draining stdin; and neither side can move. The symptom is a process holding steady at 18
    # seconds of CPU with no output -- it looks like slow work, and it is no work at all.
    proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def feed():
        try:
            proc.stdin.write(("\n".join(objs) + "\n").encode())
            proc.stdin.close()
        except OSError:
            pass                                  # git exited early; the read loop will notice

    writer = threading.Thread(target=feed, daemon=True)
    writer.start()
    n_bytes = 0
    while True:
        header = proc.stdout.readline()
        if not header:
            break
        parts = header.split()
        if len(parts) < 3:
            continue                                  # "<sha> missing" -- nothing to read
        sha, typ, size = parts[0].decode(), parts[1].decode(), int(parts[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)                           # the newline cat-file appends
        n_bytes += size
        if typ != "blob":
            continue
        path = objs.get(sha, "?")
        ext = os.path.splitext(path)[1].lower()
        do_re = ext not in SKIP_REGEX_EXT and size <= MAX_REGEX_BYTES
        for kind, line, red in scan_bytes(data, forms, do_re):
            fails.append(("%s @ blob %s:%d" % (path, sha[:10], line), kind, red, "history"))
    proc.stdout.close()
    writer.join(timeout=10)
    proc.wait()
    print("   read %.1f MB of blob content" % (n_bytes / 1e6))
    print()

    # ------------------------------------------------------------ the report
    for label, bucket in (("FAIL", fails), ("WARN", warns)):
        if bucket:
            print("%s -- %d hit(s):" % (label, len(bucket)))
            for where, kind, red, group in bucket:
                print("   [%-9s] %-28s %s  %s" % (group, kind, where, red))
            print()

    print("=" * 78)
    if fails:
        print("SCAN: %d FAILURE(S) -- do NOT publish. %d warning(s)." % (len(fails), len(warns)))
        print("=" * 78)
        return 1
    print("SCAN: CLEAN. 0 hits in %d tracked files and %d history blobs. %d warning(s)."
          % (len(tracked), len(objs), len(warns)))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
