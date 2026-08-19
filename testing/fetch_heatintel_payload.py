# -*- coding: utf-8 -*-
"""Fetch the /v1/heat_intelligence payload, then REDACT the credential FortyGuard leaked into its URL.

WHY THIS FILE EXISTS -- a severe defect found 2026-08-16
    /v1/heat_intelligence does not return data inline. It returns a `download_link` to S3, and that
    link has the CALLER'S API KEY EMBEDDED IN THE OBJECT PATH:

        .../<tier>_api/accountid%3Dacc%23<ACCOUNT>/api_key%3D<32-CHAR-KEY>/type%3D.../activity_id%3D...

    A credential in a URL path is a serious exposure: URLs travel into server access logs, browser
    history, proxy and CDN caches, and HTTP Referer headers, and they are routinely pasted into
    tickets and chat. It also means the key is written to any file that stores the response -- which
    is how it landed in our own fixture and would have been committed to a PUBLIC repository, since
    a public repo is a submission requirement for this hackathon.

WHAT THIS SCRIPT DOES
    1. Reads the saved response and extracts the download link (in memory only).
    2. Fetches the payload from S3 -- FREE, this is a plain object GET, not a metered API call.
    3. Saves the payload, then redacts the key and account id from EVERY fixture and result file.
    4. Verifies the whole working tree is clean apart from .env.

The key value is never printed.
"""
import io
import json
import os
import re
import sys
import urllib.request

from common import banner, FIXTURES, RESULTS, ROOT, load_key

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = os.path.join(FIXTURES, "probe_heatintel.json")
PAYLOAD_OUT = os.path.join(FIXTURES, "probe_heatintel_payload.json")
KEY = load_key()
PLACEHOLDER = "REDACTED_API_KEY"
ACCOUNT_RE = re.compile(r"(accountid%3Dacc%23)[A-Za-z0-9]+")


def redact(text):
    text = text.replace(KEY, PLACEHOLDER)
    return ACCOUNT_RE.sub(r"\1REDACTED_ACCOUNT", text)


def main():
    banner("heat_intelligence payload fetch + credential redaction   [FREE, S3 object GET]")

    if not os.path.exists(SRC):
        print("   %s missing -- nothing to do" % SRC)
        return 2

    saved = json.load(open(SRC, encoding="utf-8"))
    link = saved.get("download_link") if isinstance(saved, dict) else None
    if not link:
        print("   no download_link in the saved response; keys: %s"
              % (list(saved.keys()) if isinstance(saved, dict) else type(saved).__name__))
        link = None

    if link:
        print("   download_link present, %d chars." % len(link))
        print("   key embedded in the URL path: %s" % ("YES -- this is the defect" if KEY in link
                                                       else "no"))
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=120).read()
            print("   fetched %d bytes from S3 (free -- object GET, not a metered API call)" % len(raw))
            txt = raw.decode("utf-8", "replace")
            try:
                payload = json.loads(txt)
                json.dump(payload, open(PAYLOAD_OUT, "w"), indent=1, default=str)
                print("   parsed as JSON -> %s" % PAYLOAD_OUT)
                print("\n   ---- WHAT heat_intelligence ACTUALLY RETURNS ----")
                describe(payload)
            except Exception:
                open(PAYLOAD_OUT.replace(".json", ".txt"), "w", encoding="utf-8").write(txt[:200000])
                print("   not JSON; first 600 chars:")
                print("      " + txt[:600].replace("\n", "\n      "))
        except Exception as e:
            print("   S3 fetch failed: %s" % str(e)[:200])
            print("   (presigned links expire; the defect stands regardless)")

    # ---------------------------------------------------------------- redact everything
    print("\n   REDACTING the key and account id from every fixture and result file...")
    touched = []
    for base in (FIXTURES, RESULTS):
        for dirpath, dirnames, filenames in os.walk(base):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    b = open(p, "rb").read()
                except Exception:
                    continue
                if KEY.encode() not in b and b"accountid%3Dacc%23" not in b:
                    continue
                try:
                    t = b.decode("utf-8", "replace")
                except Exception:
                    continue
                open(p, "w", encoding="utf-8", newline="").write(redact(t))
                touched.append(os.path.relpath(p, ROOT))
    if touched:
        for t in touched:
            print("      redacted: %s" % t)
    else:
        print("      nothing needed redacting")

    # ---------------------------------------------------------------- verify
    print("\n   VERIFYING the whole working tree (excluding .env, which is supposed to hold it)...")
    bad = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if os.path.abspath(p) == os.path.abspath(os.path.join(ROOT, ".env")):
                continue
            try:
                if KEY.encode() in open(p, "rb").read():
                    bad.append(os.path.relpath(p, ROOT))
            except Exception:
                pass
    if bad:
        print("      !!! key still present in: %s" % bad)
        return 1
    print("      CLEAN: the key appears nowhere in the working tree except .env")
    return 0


def describe(obj, indent=6, depth=0):
    pad = " " * indent
    if depth > 4:
        return
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:30]:
            if isinstance(v, dict):
                print("%s%s: dict(%d) %s" % (pad, k, len(v), list(v.keys())[:10]))
                describe(v, indent + 3, depth + 1)
            elif isinstance(v, list):
                print("%s%s: list(%d)" % (pad, k, len(v)))
                if v:
                    if isinstance(v[0], (dict, list)):
                        describe(v[0], indent + 3, depth + 1)
                    else:
                        print("%s   e.g. %r" % (pad, v[0]))
            elif isinstance(v, str) and len(v) > 300:
                print("%s%s: str %d chars -- %s" % (pad, k, len(v), v[:250]))
            else:
                print("%s%s: %r" % (pad, k, v))
    elif isinstance(obj, list):
        print("%slist(%d)" % (pad, len(obj)))
        if obj:
            describe(obj[0], indent + 3, depth + 1)


if __name__ == "__main__":
    sys.exit(main())
