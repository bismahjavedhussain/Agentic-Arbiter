# -*- coding: utf-8 -*-
"""Screen the top clear-path candidates for COOLING ARCHITECTURE. FREE, keyless.

WHY
---
`refusal_rank.py` ranks pairs by measured plume-path clearance. It says nothing about whether the
cooling equipment is at GRADE or on the ROOF -- and PLAN section 8d's scope statement depends entirely
on that, because it is what makes FortyGuard's 2 m measurement plane the plane the equipment breathes.

Those two criteria turned out to CONFLICT. The top refusal-ranked pair (597970809 / 597970806, Digital
Realty Northern Virginia IAD35 / IAD36) has a perfectly clear plume path AND roofs densely covered in
regular equipment arrays in both USGS and ESRI imagery -- i.e. it looks ROOFTOP-cooled, which section 8d
puts explicitly OUT of scope. Selecting for physics broke the scope premise.

So this script fetches a tight ESRI frame for each of the top N clear-path candidates so the
architecture of each can actually be LOOKED AT before one is committed. It does not classify anything
automatically: at 0.3-0.5 m we see objects, not nameplates, so classification stays a human judgement
recorded in PLAN section 8d.

Ranking note: candidates are taken in `usable_exposure` order but ONLY from pairs measured at 0 %
refused, because a pair that refuses is disqualified on the physics regardless of its architecture.
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
# METRO-AWARE; ashburn keeps its original paths so the audited chain is untouched.
sys.path.insert(0, _HERE)
import metros as _M                                                        # noqa: E402
RANK = _M.geom_path("refusal_rank.json")
CAND = _M.candidates_path()
# imagery goes in a per-metro subfolder; ashburn keeps the flat screen/ directory it already uses
OUT = (os.path.join(ROOT, "data", "imagery", "screen") if _M.metro_key() == _M.DEFAULT_METRO
       else os.path.join(ROOT, "data", "imagery", "screen", _M.metro_key()))
os.makedirs(OUT, exist_ok=True)

ESRI = ("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export")
N_TOP = 8
PAD_LAT, PAD_LON = 0.0009, 0.0012      # ~200 x 200 m around the pair -- tight enough to see units


def fetch(bbox, path):
    params = {"bbox": "%.6f,%.6f,%.6f,%.6f" % bbox, "bboxSR": "4326", "imageSR": "3857",
              "size": "1400,1050", "format": "png32", "transparent": "false", "f": "image"}
    url = ESRI + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "INTAKE-ARBITER/1.0 (research)"})
        raw = urllib.request.urlopen(req, timeout=180).read()
    except Exception as ex:
        return None, str(ex)[:100]
    if len(raw) < 2000:
        return None, "only %d bytes" % len(raw)
    open(path, "wb").write(raw)
    return len(raw), None


def main():
    rank = json.load(open(RANK, encoding="utf-8"))
    B = {b["osm_id"]: b for b in json.load(open(CAND, encoding="utf-8"))["buildings"]}
    clear = [r for r in rank["ranked"] if (r["refused_downwind_frac"] or 0.0) <= 0.001]

    print("=" * 96)
    print("  ARCHITECTURE SCREEN -- top %d clear-path candidates (of %d fully clear, %d ranked)"
          % (N_TOP, len(clear), rank["n_measured"]))
    print("  Fetching tight ESRI frames so GRADE vs ROOFTOP equipment can be seen. FREE, keyless.")
    print("=" * 96)

    manifest = []
    for i, r in enumerate(clear[:N_TOP], 1):
        a, b = B.get(r["source_osm_id"]), B.get(r["receptor_osm_id"])
        if not (a and b):
            continue
        la, lo = a["centre_latlon"], b["centre_latlon"]
        bbox = (min(la[1], lo[1]) - PAD_LON, min(la[0], lo[0]) - PAD_LAT,
                max(la[1], lo[1]) + PAD_LON, max(la[0], lo[0]) + PAD_LAT)
        tag = "%02d_%d_%d" % (i, r["source_osm_id"], r["receptor_osm_id"])
        path = os.path.join(OUT, "%s.png" % tag)
        n, err = fetch(bbox, path)
        nm = (r["source_name"] or "-")[:34]
        print("  %2d. %-11d %-11d gap %5.0f m  facade %4.0f m  usable %.4f  %-34s  %s"
              % (i, r["source_osm_id"], r["receptor_osm_id"], r["true_gap_m"],
                 r["longest_facade_m"], r["usable_exposure"], nm,
                 ("%d bytes" % n) if n else ("FAILED %s" % err)))
        manifest.append({"rank": i, "file": os.path.basename(path),
                         "source_osm_id": r["source_osm_id"], "receptor_osm_id": r["receptor_osm_id"],
                         "source_name": r["source_name"], "receptor_name": r["receptor_name"],
                         "true_gap_m": r["true_gap_m"], "longest_facade_m": r["longest_facade_m"],
                         "usable_exposure": r["usable_exposure"],
                         "source_latlon": la, "receptor_latlon": lo, "bbox": list(bbox),
                         "architecture_verdict": "NOT YET ASSESSED -- record in PLAN section 8d"})

    json.dump({"purpose": "screen clear-path candidates for grade vs rooftop cooling before "
                          "committing a site; section 8d's scope statement depends on it",
               "source": "ESRI World Imagery, ArcGIS REST export. Cross-check with USGS before "
                         "asserting anything in PLAN.",
               "caveat": "0.3-0.5 m resolution shows objects, not nameplates. Cannot certify unit type "
                         "or measure heights.",
               "candidates": manifest},
              open(os.path.join(OUT, "screen_manifest.json"), "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n  %d frame(s) in %s" % (len(manifest), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
