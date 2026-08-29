"""Fetch and prepare the four Earth textures the hero globe needs.

WHY THIS IS A SCRIPT AND NOT FOUR DOWNLOADS. The same reason `tools/make_swell.py` exists: an asset
that arrived by hand is an asset nobody can reproduce, and two of these four need a FORMAT CONVERSION
that a browser cannot do for itself. Running this again from a clean tree produces byte-comparable
files and prints the payload, which is the number the brief caps.

THE SOURCE: solarsystemscope.com/textures, CC BY 4.0 (attribution, commercial use permitted). The
licence line is written to demo/textures/CREDITS.txt by this script, so the attribution ships beside
the files it covers rather than depending on someone remembering to add it.

SELF-HOSTED, NEVER HOTLINKED. Two reasons, and the first is a standing requirement of this project:
the shipped artefact must work offline, which a CDN reference cannot. The second is that a texture
that 404s leaves a black sphere with no error, which is indistinguishable from a shader bug.

TWO OF THE FOUR ARE TIFF AT SOURCE, AND NO BROWSER DECODES TIFF. `2k_earth_normal_map` and
`2k_earth_specular_map` are only published as .tif (the .jpg names 404). Both are converted here.
That is the whole reason a conversion step exists; it is not recompression for its own sake.

THE BUDGET IS ~2 MB TOTAL and the raw files come to 2.24 MB, so they are re-encoded. Quality is
chosen per MAP TYPE rather than uniformly, because the maps are read differently by the shader:

  daymap    q82   the only one a reader actually looks at; artefacts here are visible
  clouds    q74   used as an alphaMap, so ONLY its luminance is read: greyscale, 1 channel not 3.
                  Drawn at opacity 0.4 over a rotating sphere, where ringing is invisible
  normal    PNG   LOSSLESS, AND MEASURED RATHER THAN CHOSEN. See below
  specular  q78   a land/ocean mask read as one channel. Greyscale, and the softest of the four

🔴 THE NORMAL MAP IS THE ONE THAT CANNOT BE JPEG, AND THE MEASUREMENT IS WHY.
Measured on the source TIFF: mean (127.99, 127.97, 255.0), stddev (1.36, 1.76, 0.00), extrema R
89..166 G 79..174. So the blue channel is a CONSTANT 255 and the whole relief signal lives in a few
units of R and G around the flat 128. That is physically correct rather than a bad asset: Earth's
relief is about 9 km on a 6,371 km radius, so a correctly scaled normal map is nearly flat, with the
deviation concentrated in the Andes and the Himalayas.
Two consequences follow, and both are settled by numbers rather than taste:
  1. It has to be AMPLIFIED to read at all, which `normalScale` in HeatGlobe.tsx does.
  2. It therefore cannot be JPEG. Encoding it at q88 dropped the stddev from 1.36 to 1.00, i.e. a
     quarter of the entire signal, and amplifying what is left amplifies the block noise with it.
     PNG keeps all of it for 463 KB, which the budget affords.
⚠ Do not "optimise" this back to JPEG on the grounds that the other three are.

Run from the repository root:  python tools/make_earth_textures.py
"""
import io
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "textures")

BASE = "https://www.solarsystemscope.com/textures/download/"

# (remote name, local name, mode, quality). `mode` is the PIL mode to convert to before encoding:
# "L" is greyscale, which is correct wherever the shader reads a single channel. A quality of None
# means PNG, i.e. lossless, which only the normal map needs and for the measured reason above.
JOBS = [
    ("2k_earth_daymap.jpg",        "earth_daymap.jpg",   "RGB", 82),
    ("2k_earth_clouds.jpg",        "earth_clouds.jpg",   "L",   74),
    ("2k_earth_normal_map.tif",    "earth_normal.png",   "RGB", None),
    ("2k_earth_specular_map.tif",  "earth_specular.jpg", "L",   78),
]

CREDITS = """Earth textures: source, licence and what each one is for
=========================================================

Files in this directory:

    earth_daymap.jpg     colour (albedo) map, the satellite image of land and ocean
    earth_clouds.jpg     cloud cover, read as an alpha map on a second, slightly larger sphere
    earth_normal.png     surface normals, which is what gives mountains and coasts their relief
    earth_specular.jpg   where the surface is shiny, so oceans catch the light and land does not

SOURCE
    Solar System Scope, https://www.solarsystemscope.com/textures/
    "2k_earth_daymap", "2k_earth_clouds", "2k_earth_normal_map", "2k_earth_specular_map"

LICENCE
    Creative Commons Attribution 4.0 International (CC BY 4.0)
    https://creativecommons.org/licenses/by/4.0/
    Attribution: Solar System Scope (solarsystemscope.com). Textures by Solar System Scope,
    based on NASA elevation and imagery data.
    Commercial use is permitted under this licence. Attribution is required, which is what this
    file is.

WHAT WAS CHANGED FROM THE ORIGINALS
    The two map files are published only as TIFF, which no browser decodes. The specular map was
    converted to greyscale JPEG; the normal map was converted to LOSSLESS PNG, because its relief
    signal is only a few units wide and has to be amplified in the shader, so a lossy encoding would
    amplify its own artefacts. The colour and cloud maps were re-encoded to hold the total payload
    under the 2 MB budget the brief sets.
    Nothing was cropped, recoloured or resampled: the pixel dimensions are the originals'.
    The conversion is reproducible: tools/make_earth_textures.py

    The 2k versions are used deliberately rather than the 8k ones. At the size this globe is drawn
    the 8k files would cost about sixteen times the bytes for detail no viewport can resolve.
"""


def main():
    try:
        from PIL import Image, ImageStat
    except ImportError:
        print("Pillow is required: python -m pip install pillow")
        return 1

    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    total = 0
    raw_total = 0
    for remote, local, mode, quality in JOBS:
        url = BASE + remote
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read()
        raw_total += len(raw)

        im = Image.open(io.BytesIO(raw))
        w, h = im.size
        src_mode = im.mode
        if im.mode != mode:
            im = im.convert(mode)
        dest = os.path.join(OUT, local)
        if quality is None:
            im.save(dest, "PNG", optimize=True)
        else:
            # progressive: a large JPEG over a slow link paints coarse-to-fine rather than
            # top-to-bottom, which matters here because these load while the reader is looking at
            # the hero.
            im.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)
        size = os.path.getsize(dest)
        total += size

        # 🔴 REPORT THE SIGNAL, NOT ONLY THE SIZE. A texture that encoded to a plausible number of
        # bytes and lost its detail looks exactly like a success here. stddev is what caught the
        # normal map: an amplified map has to keep the variation it is going to amplify.
        st = ImageStat.Stat(Image.open(dest).convert(mode))
        print("   %-20s %5dx%-5d %-4s -> %-4s %-5s %8d B  (from %8d B %s)  stddev %s"
              % (local, w, h, src_mode, mode,
                 "PNG" if quality is None else "q%d" % quality, size, len(raw),
                 os.path.splitext(remote)[1], [round(x, 2) for x in st.stddev]))

    with io.open(os.path.join(OUT, "CREDITS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(CREDITS)

    print()
    print("   raw from source   %8d B  (%.2f MB)" % (raw_total, raw_total / 1048576.0))
    print("   shipped payload   %8d B  (%.2f MB)" % (total, total / 1048576.0))
    print("   budget            %8d B  (2.00 MB)" % (2 * 1048576))
    print("   %s" % ("WITHIN BUDGET" if total < 2 * 1048576 else "OVER BUDGET"))
    print("   CREDITS.txt written beside them, CC BY 4.0 attribution")
    return 0 if total < 2 * 1048576 else 1


if __name__ == "__main__":
    sys.exit(main())
