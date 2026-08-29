"""Measure the exact duration of each MP3 in demo/audio by counting its MPEG frames.

WHY NOT TRUST THE STATED LENGTHS. The brief supplies approximate ones ("~7s", "1.9s", "3.2s") and the
cinematic timeline's beats are derived from the voiceover's length, so an approximation compounds: the
hold after the voice, the whoosh cue and the crossfade all sit at offsets from it. This project has
measured that number once before, when the voiceover was 4.676 s, and the file has since been replaced.

WHY FRAME HEADERS AND NOT A LIBRARY. There is no audio library in this repository and adding one to
learn a duration would be a dependency for a constant. An MP3's duration is exactly
`frames * samples_per_frame / sample_rate`, and both figures are in every frame's 4-byte header, so
counting frames is the measurement rather than an estimate of it.

⚠ CBR IS ASSUMED ONLY FOR THE SANITY CHECK, not for the duration. The frame walk reads each header's
own bitrate, so a variable-bitrate file is measured correctly; the script reports whether the bitrate
varied so a reader knows which case they are in.

Run from the repository root:  python tools/measure_audio.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "audio")

# MPEG version -> layer -> bitrate table index. Only what MP3 needs.
BITRATES = {
    # MPEG 1 Layer III
    (3, 1): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
    # MPEG 2 / 2.5 Layer III
    (2, 1): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
}
RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}
# Samples per frame: MPEG 1 Layer III is 1152, MPEG 2/2.5 Layer III is 576.
SPF = {3: 1152, 2: 576, 0: 576}


def measure(path):
    b = io.open(path, "rb").read()
    i = 0
    n = len(b)

    # Skip an ID3v2 tag if present: 'ID3' then a 4-byte syncsafe size after a 6-byte header.
    if b[:3] == b"ID3":
        size = (b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9]
        i = 10 + size

    frames = 0
    samples = 0
    rates = set()
    bitrates = set()
    while i + 4 <= n:
        if b[i] != 0xFF or (b[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        ver_bits = (b[i + 1] >> 3) & 0x03      # 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5
        layer_bits = (b[i + 1] >> 1) & 0x03    # 1 = Layer III
        br_index = (b[i + 2] >> 4) & 0x0F
        sr_index = (b[i + 2] >> 2) & 0x03
        pad = (b[i + 2] >> 1) & 0x01
        if ver_bits == 1 or layer_bits != 1 or br_index in (0, 15) or sr_index == 3:
            i += 1
            continue
        key = (3 if ver_bits == 3 else 2, layer_bits)
        if key not in BITRATES:
            i += 1
            continue
        bitrate = BITRATES[key][br_index] * 1000
        rate = RATES[ver_bits][sr_index]
        spf = SPF[ver_bits]
        length = int(spf / 8 * bitrate / rate) + pad
        if length <= 4:
            i += 1
            continue
        frames += 1
        samples += spf
        rates.add(rate)
        bitrates.add(bitrate // 1000)
        i += length

    if not frames or not rates:
        return None
    rate = sorted(rates)[0]
    return {
        "frames": frames,
        "samples": samples,
        "rate": rate,
        "seconds": samples / float(rate),
        "bitrates": sorted(bitrates),
        "bytes": n,
    }


def main():
    if not os.path.isdir(AUDIO):
        print("no audio directory at %s" % AUDIO)
        return 1
    names = sorted(f for f in os.listdir(AUDIO) if f.lower().endswith((".mp3", ".wav")))
    if not names:
        print("no audio files")
        return 1
    total = 0
    print("   %-26s %10s %8s %7s %9s %s" % ("file", "bytes", "frames", "rate", "seconds", "kbps"))
    for f in names:
        p = os.path.join(AUDIO, f)
        total += os.path.getsize(p)
        if not f.lower().endswith(".mp3"):
            print("   %-26s %10d   (not an MP3, not measured here)" % (f, os.path.getsize(p)))
            continue
        m = measure(p)
        if not m:
            print("   %-26s %10d   NO MPEG FRAMES FOUND" % (f, os.path.getsize(p)))
            continue
        kbps = m["bitrates"][0] if len(m["bitrates"]) == 1 else "VBR %s" % m["bitrates"]
        print("   %-26s %10d %8d %7d %9.3f %s"
              % (f, m["bytes"], m["frames"], m["rate"], m["seconds"], kbps))
    print()
    print("   total payload %d bytes (%.2f MB)" % (total, total / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
