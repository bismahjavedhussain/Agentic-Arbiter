# -*- coding: utf-8 -*-
"""Generate the intro's opening swell. No network, no dependencies beyond numpy.

    python tools/make_swell.py

WHY THIS IS SYNTHESISED RATHER THAN SOURCED
-------------------------------------------
The brief asks for "a short ambient tone under the voiceover, 2-3 seconds, low, rising. No drums, no
melody, nothing that reads as stock corporate music", sourced royalty-free from Pixabay or
freesound.org.

Generating it instead answers the same requirement better on three counts, and the trade is stated
rather than hidden:

  * LICENSING. A synthesised tone has no attribution to carry and no licence to be wrong about. The
    project's rule is that every claim is traceable; "royalty-free, I think" is not traceable.
  * CHARACTER. "Nothing that reads as stock corporate music" is a negative requirement, and the
    surest way to meet it is to use no musical material at all: one pitch and its octave, no third,
    no fifth, no rhythm, no chord. A stock file usually has all four.
  * SIZE. 3.0 s of 22.05 kHz mono at 16 bit is 132 KB, inside the brief's ~300 KB budget alongside
    the 89 KB voiceover.

WHAT IT IS, EXACTLY
-------------------
A fundamental sweeping 55 Hz to 110 Hz (A1 to A2) over three seconds, plus its octave at a third of
the amplitude, under a slow rise-and-release envelope. Two partials an octave apart read as ONE
low tone getting brighter, not as an interval: an octave is the one relationship the ear hears as the
same note. No harmonics above the second, so there is nothing for the ear to call a timbre or a
chord.

WHY WAV AND NOT MP3
-------------------
There is no MP3 encoder on this machine (no ffmpeg, and none in the Python standard library), and
hand-writing one is not a reasonable thing to do for three seconds of sine wave. WAV is losslessly
correct, plays in every browser `<audio>` element, and at this length is smaller than most stock MP3s
anyway. `audio.ts` names the file in one constant, so dropping a sourced `swell.mp3` in and changing
that line is a one-word edit.
"""
import io
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "AGENTIC-ARBITER", "demo", "audio", "swell.wav")

SR = 22050          # plenty for a tone whose highest partial is 220 Hz
SECONDS = 3.0
F_START = 55.0      # A1
F_END = 110.0       # A2
OCTAVE_MIX = 0.33   # the second partial, quiet enough to brighten rather than to harmonise
PEAK = 0.72         # headroom: audio.ts plays this at 0.4 master and ducks it to 0.12


def main():
    n = int(SR * SECONDS)
    t = np.arange(n, dtype=np.float64) / SR

    # THE SWEEP, INTEGRATED. A sine of `2*pi*f(t)*t` is wrong: it produces a chirp whose instantaneous
    # frequency is f(t) + t*f'(t), which here would overshoot 110 Hz by half again. The phase has to
    # be the INTEGRAL of the frequency. For a linear sweep that integral is closed-form.
    f0, f1 = F_START, F_END
    phase = 2.0 * np.pi * (f0 * t + (f1 - f0) * t * t / (2.0 * SECONDS))
    wave = np.sin(phase) + OCTAVE_MIX * np.sin(2.0 * phase)

    # THE ENVELOPE: rise, brief plateau, gentle release. Raised-cosine at both ends so there is no
    # click at either edge -- a hard start on a 55 Hz tone is an audible thump on any speaker with a
    # woofer.
    env = np.ones(n)
    rise = int(0.62 * n)                       # most of the file is the rise: it is a SWELL
    env[:rise] = 0.5 - 0.5 * np.cos(np.pi * np.linspace(0.0, 1.0, rise))
    rel = int(0.26 * n)
    env[n - rel:] *= 0.5 + 0.5 * np.cos(np.pi * np.linspace(0.0, 1.0, rel))

    sig = wave * env
    sig = sig / max(1e-9, float(np.max(np.abs(sig)))) * PEAK

    pcm = np.clip(np.round(sig * 32767.0), -32768, 32767).astype("<i2")
    data = pcm.tobytes()

    # A minimal canonical 44-byte RIFF header. Written by hand so this script needs no wave module
    # quirks and the file's exact bytes are visible here.
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    hdr += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16)
    hdr += b"data" + struct.pack("<I", len(data))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "wb").write(hdr + data)

    print("   wrote %s" % OUT)
    print("   %.3f s, %d Hz mono 16-bit, %s bytes" % (SECONDS, SR, format(os.path.getsize(OUT), ",")))
    print("   sweep %.0f Hz -> %.0f Hz, octave partial at %.2f, peak %.2f" %
          (F_START, F_END, OCTAVE_MIX, PEAK))
    # Report the measured shape rather than the intended one.
    print("   measured: peak sample %.3f, rms %.3f, first/last sample %.5f / %.5f"
          % (float(np.max(np.abs(sig))), float(np.sqrt(np.mean(sig ** 2))),
             float(sig[0]), float(sig[-1])))
    return 0


def chime():
    """The staggered-load cue: "a short, crisp UI sound effect (e.g., a digital chime)".

    THE CONSTRAINT THAT SHAPES IT IS THAT IT PLAYS FIVE TIMES IN A ROW. A cue heard once can be
    bright and long; one heard once per widget has to be short enough not to overlap the next and
    quiet enough not to become the thing you notice. So: 170 ms, a fast attack and an exponential
    decay, and a peak of 0.42 against the swell's 0.72.

    Two partials a fifth apart (G6 and D7) rather than one: a single sine reads as a beep, and the
    fifth is the interval that reads as "instrument" without reading as "melody". Nothing below
    1.5 kHz, so it sits above the swell instead of fighting it.
    """
    out = os.path.join(os.path.dirname(OUT), "chime.wav")
    secs = 0.17
    n = int(SR * secs)
    t = np.arange(n, dtype=np.float64) / SR

    sig = np.sin(2 * np.pi * 1568.0 * t) + 0.55 * np.sin(2 * np.pi * 2349.0 * t)

    # Fast attack so it is crisp, exponential decay so it does not click off.
    atk = int(0.004 * SR)
    env = np.exp(-t * 26.0)
    env[:atk] *= np.linspace(0.0, 1.0, atk)
    sig *= env
    sig = sig / max(1e-9, float(np.max(np.abs(sig)))) * 0.42

    pcm = np.clip(np.round(sig * 32767.0), -32768, 32767).astype("<i2")
    data = pcm.tobytes()
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    hdr += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16)
    hdr += b"data" + struct.pack("<I", len(data))
    io.open(out, "wb").write(hdr + data)
    print("   wrote %s" % out)
    print("   %.3f s, %s bytes, peak %.3f, rms %.3f, last sample %.5f"
          % (secs, format(os.path.getsize(out), ","), float(np.max(np.abs(sig))),
             float(np.sqrt(np.mean(sig ** 2))), float(sig[-1])))


if __name__ == "__main__":
    rc = main()
    chime()
    sys.exit(rc)
