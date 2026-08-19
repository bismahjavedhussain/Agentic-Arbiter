# -*- coding: utf-8 -*-
"""Fetch public aerial imagery of the selected halls so the cooling architecture can be SEEN.

FREE, keyless. Two independent sources so one can check the other:
  1. USGS National Map "USGSImageryOnly" -- US federal imagery, PUBLIC DOMAIN, cleanest licensing.
  2. ESRI World Imagery -- often higher resolution in urban US, used for cross-checking only.

Both expose an ArcGIS REST `export` endpoint that returns ONE image for a bbox, which avoids having
to stitch a tile grid.

The question being answered: does this campus use ground-level equipment yards, rooftop chiller units,
or wall louvers with roof exhaust fans? That determines whether FortyGuard's 2 m measurement plane is
the plane the equipment actually breathes -- i.e. whether PLAN section 8d's scope statement holds here.

COORDINATES ARE READ FROM `data/geometry/selected_site.json`, NOT hard-coded.
    They were hard-coded to the original AWS pair (IAD119 / IAD118). When the site was re-selected on
    2026-08-18 after N-54, those constants would have silently kept fetching imagery of a site the
    project no longer models -- and the scope statement would have rested on pictures of the wrong
    buildings. Reading the selection file makes that impossible. Falls back to the old pair only if the
    file cannot be read, and says so loudly.
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
OUT = os.path.join(ROOT, "data", "imagery")   # NOT src/ -- images are data
os.makedirs(OUT, exist_ok=True)
SEL = os.path.join(ROOT, "data", "geometry", "selected_site.json")

FALLBACK_SOURCE = (39.017236, -77.439130)      # IAD119, the ORIGINAL pair
FALLBACK_RECEPTOR = (39.018398, -77.438473)    # IAD118, the ORIGINAL pair


def load_pair():
    """(source_latlon, receptor_latlon, label) from the live selection file."""
    try:
        d = json.load(open(SEL, encoding="utf-8"))
        a, b = d["source_building"], d["receptor_building"]
        la, lb = a["centre_latlon"], b["centre_latlon"]
        lbl = "%s %s -> %s %s" % (a["osm_id"], a.get("name") or a.get("operator"),
                                  b["osm_id"], b.get("name") or b.get("operator"))
        return tuple(la), tuple(lb), lbl
    except Exception as ex:
        print("   *** COULD NOT READ %s (%s)" % (os.path.basename(SEL), str(ex)[:90]))
        print("   *** falling back to the ORIGINAL hard-coded pair -- imagery may be of the WRONG site")
        return FALLBACK_SOURCE, FALLBACK_RECEPTOR, "FALLBACK original AWS pair"


SOURCE, RECEPTOR, PAIR_LABEL = load_pair()

SERVICES = {
    "usgs": ("https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/"
             "MapServer/export"),
    "esri": ("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
             "MapServer/export"),
}


def bbox_around(pts, pad_lat, pad_lon):
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    return (min(lons) - pad_lon, min(lats) - pad_lat,
            max(lons) + pad_lon, max(lats) + pad_lat)


def fetch(service, url, bbox, size, tag):
    params = {
        "bbox": "%.6f,%.6f,%.6f,%.6f" % bbox,
        "bboxSR": "4326",
        "imageSR": "3857",
        "size": "%d,%d" % size,
        "format": "png32",
        "transparent": "false",
        "f": "image",
    }
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(full, headers={"User-Agent": "INTAKE-ARBITER/1.0 (research)"})
        raw = urllib.request.urlopen(req, timeout=180).read()
    except Exception as ex:
        print("   %-6s FAILED: %s" % (service, str(ex)[:140]))
        return None
    if len(raw) < 2000:
        print("   %-6s returned only %d bytes -- probably an error tile" % (service, len(raw)))
        return None
    p = os.path.join(OUT, "%s_%s.png" % (service, tag))
    open(p, "wb").write(raw)
    try:
        from PIL import Image
        im = Image.open(p)
        print("   %-6s %5d x %-5d  %7d bytes  -> %s" % (service, im.width, im.height, len(raw), p))
    except Exception:
        print("   %-6s %7d bytes -> %s" % (service, len(raw), p))
    return p


def main():
    print("=" * 78)
    print("Aerial imagery of the CURRENTLY SELECTED pair, read from selected_site.json:")
    print("   %s" % PAIR_LABEL)
    print("=" * 78)

    # two framings: the pair in context, and a tight crop on the gap between them
    wide = bbox_around([SOURCE, RECEPTOR], 0.0016, 0.0022)
    tight = bbox_around([SOURCE, RECEPTOR], 0.0007, 0.0009)

    span_m_lat = (wide[3] - wide[1]) * 111320.0
    span_m_lon = (wide[2] - wide[0]) * 111320.0 * 0.777
    print("\n   WIDE  bbox %.6f,%.6f,%.6f,%.6f  ~= %.0f x %.0f m"
          % (wide + (span_m_lon, span_m_lat)))
    span_m_lat_t = (tight[3] - tight[1]) * 111320.0
    span_m_lon_t = (tight[2] - tight[0]) * 111320.0 * 0.777
    print("   TIGHT bbox %.6f,%.6f,%.6f,%.6f  ~= %.0f x %.0f m"
          % (tight + (span_m_lon_t, span_m_lat_t)))

    got = {}
    for tag, bb, size in (("wide", wide, (1600, 1200)), ("tight", tight, (1600, 1200))):
        print("\n   fetching %s framing:" % tag)
        for svc, url in SERVICES.items():
            p = fetch(svc, url, bb, size, tag)
            if p:
                got["%s_%s" % (svc, tag)] = p

    json.dump({
        "site": {"pair_label": PAIR_LABEL,
                 "source_latlon": list(SOURCE), "receptor_latlon": list(RECEPTOR),
                 "read_from": "data/geometry/selected_site.json -- NOT hard-coded, see the docstring",
                 "address": "resolve from the coordinates; do not hard-code, the site changed once"},
        "bbox_wide": list(wide), "bbox_tight": list(tight),
        "files": got,
        "attribution": {
            "usgs": "USGS The National Map, USGSImageryOnly -- US federal imagery, public domain",
            "esri": "ESRI World Imagery -- used for cross-checking resolution only",
        },
        "purpose": "determine whether cooling equipment is in a ground-level yard, on the roof, or "
                   "wall louvers with roof exhaust -- decides whether FortyGuard's 2 m plane applies",
    }, open(os.path.join(OUT, "imagery_manifest.json"), "w"), indent=1, allow_nan=False)
    print("\n   %d image(s) fetched" % len(got))
    return 0


if __name__ == "__main__":
    sys.exit(main())
