# -*- coding: utf-8 -*-
"""Draw the SOURCE and RECEPTOR onto each screening frame, so the pair can be judged. FREE.

    METRO=chicago python annotate_screen.py
    python annotate_screen.py --all

--------------------------------------------------------------------------------------------
WHY THIS EXISTS
--------------------------------------------------------------------------------------------
`screen_architecture.py` fetches a tight aerial frame per candidate pair so a human can decide
whether the cooling equipment is at GRADE or on the ROOF -- the scope gate PLAN section 8d depends
on. But the frames come back as RAW imagery: a Chicago frame holds about ten buildings, several of
them warehouses with trailer docks, and NOTHING marks which two are the pair being judged.

Asking anyone to arbitrate that is unreasonable, and asking a beginner to is worse -- the honest
answer to "which building am I looking at" was "you cannot tell". So this overlays the actual OSM
footprint rings of the source and the receptor, labels them, and draws the plume direction between
them. Everything is projected from the frame's own bbox in `screen_manifest.json`, so the overlay
cannot disagree with the image it is drawn on.

    Source   = RED    (the hall blowing hot exhaust out)
    Receptor = BLUE   (the hall breathing it in)
    Arrow    = the direction the plume travels when the wind is on the critical bearing

The verdict itself stays a human judgement, recorded in architecture_verdicts.json. This only makes
the judgement POSSIBLE.
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import metros as M                                                          # noqa: E402

RED = (235, 104, 52)
BLUE = (57, 135, 229)
WHITE = (255, 255, 255)


def screen_dir(k):
    base = os.path.join(ROOT, "data", "imagery", "screen")
    return base if k == M.DEFAULT_METRO else os.path.join(base, k)


def ring_latlon(b, cand):
    """Footprint ring back in lat/lon. The candidates file stores metres in a local frame plus the
    building's centre lat/lon, so the ring is re-projected about that centre -- the same
    equirectangular convention fetch_geometry used to create it."""
    la0, lo0 = b["centre_latlon"]
    cx, cy = b["centre_m"]
    mlat = 111132.0
    mlon = 111320.0 * math.cos(math.radians(la0))
    return [(lo0 + (p[0] - cx) / mlon, la0 + (p[1] - cy) / mlat) for p in b["ring_m"]]


def draw_pair(mkey, entry, cand_by_id, out_dir):
    path = os.path.join(out_dir, entry["file"])
    if not os.path.exists(path):
        return None
    w, s, e, n = entry["bbox"][0], entry["bbox"][1], entry["bbox"][2], entry["bbox"][3]
    im = Image.open(path).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)

    def xy(lon, lat):
        return ((lon - w) / (e - w) * W, (1.0 - (lat - s) / (n - s)) * H)

    for oid, col, tag in ((entry["source_osm_id"], RED, "SOURCE (exhaust)"),
                          (entry["receptor_osm_id"], BLUE, "RECEPTOR (intake)")):
        b = cand_by_id.get(oid)
        if not b:
            continue
        pts = [xy(lo, la) for lo, la in ring_latlon(b, cand_by_id)]
        # a white halo under the coloured outline so it reads over both bright roofs and dark asphalt
        d.line(pts + [pts[0]], fill=WHITE, width=7)
        d.line(pts + [pts[0]], fill=col, width=3)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        label = "%s  %s" % (tag, b.get("name") or b.get("operator") or oid)
        tw = 7 * len(label)
        d.rectangle([cx - tw / 2 - 4, cy - 11, cx + tw / 2 + 4, cy + 11], fill=WHITE)
        d.text((cx - tw / 2, cy - 6), label, fill=col)

    a = xy(entry["source_latlon"][1], entry["source_latlon"][0])
    b2 = xy(entry["receptor_latlon"][1], entry["receptor_latlon"][0])
    d.line([a, b2], fill=WHITE, width=8)
    d.line([a, b2], fill=(0, 0, 0), width=2)
    # arrow head at the receptor end
    ang = math.atan2(b2[1] - a[1], b2[0] - a[0])
    for off in (2.6, -2.6):
        d.line([b2, (b2[0] + 22 * math.cos(ang + off), b2[1] + 22 * math.sin(ang + off))],
               fill=(0, 0, 0), width=2)
    cap = "%s -> %s   gap %.0f m" % (
        (cand_by_id.get(entry["source_osm_id"], {}).get("name") or entry["source_osm_id"]),
        (cand_by_id.get(entry["receptor_osm_id"], {}).get("name") or entry["receptor_osm_id"]),
        entry.get("true_gap_m") or 0)
    d.rectangle([0, 0, 10 + 7 * len(cap), 22], fill=WHITE)
    d.text((6, 6), cap, fill=(0, 0, 0))

    out = os.path.join(out_dir, "annotated_" + entry["file"])
    im.save(out)
    return out


def run(mkey):
    sd = screen_dir(mkey)
    man = os.path.join(sd, "screen_manifest.json")
    if not os.path.exists(man):
        print("   %-11s no screen_manifest.json -- run screen_architecture.py first" % mkey)
        return 1
    entries = json.load(open(man, encoding="utf-8"))["candidates"]
    cand = json.load(open(M.candidates_path(mkey), encoding="utf-8"))
    by_id = {b["osm_id"]: b for b in cand["buildings"]}
    made = [draw_pair(mkey, en, by_id, sd) for en in entries]
    made = [m for m in made if m]
    print("   %-11s annotated %d of %d frames -> %s"
          % (mkey, len(made), len(entries), os.path.relpath(sd, ROOT)))
    for en, m in zip(entries, made):
        print("      rank %d  %s -> %s   gap %.0f m   %s"
              % (en["rank"], en.get("source_name") or en["source_osm_id"],
                 en.get("receptor_name") or en["receptor_osm_id"],
                 en.get("true_gap_m") or 0, os.path.basename(m)))
    return 0


def main(argv):
    print("=" * 78)
    print("ANNOTATE SCREENING FRAMES -- red = source, blue = receptor, arrow = plume direction")
    print("=" * 78)
    keys = sorted(M.METROS) if "--all" in argv else [M.metro_key()]
    rc = 0
    for k in keys:
        rc |= run(k)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
