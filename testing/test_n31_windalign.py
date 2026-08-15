# -*- coding: utf-8 -*-
"""N-31  ---  does FortyGuard's 60 m field contain WIND-DEPENDENT spatial structure?   FREE.

THE QUESTION, AND WHY BOTH ANSWERS MATTER
    Our physics adds a plume: heat leaves a condenser, the wind carries it, some reaches an intake.
    Before adding anything we must know whether FortyGuard's field ALREADY contains such structure.

        if YES  we are DOUBLE-COUNTING and must subtract their contribution
        if NO   it confirms the value proposition -- they cannot see it, we add it -- and it becomes
                a defensible feature request rather than a guess

    This is a correctness check on the whole chain, not a tuning exercise. It is the one test that
    could reveal we are adding something twice.

NO NEW API CALLS
    Uses 25 fields already paid for: the same 2 x 2 km AOI at 100 m granularity, on five dates
    (2026-06-15, 06-30, 07-10, 07-20, 07-28) at five two-hour windows each (10:00-12:00 through
    18:00-20:00, site-local). Date AND hour are known exactly for every one, which is what makes the
    wind matching valid.

WIND DATA
    FortyGuard serves no wind, so wind comes from KIAD (Washington Dulles), the ASOS station inside
    the AOI, via the Iowa State University Environmental Mesonet archive -- free, public, hourly, and
    reported in America/New_York, the same site-local convention the FortyGuard endpoint uses (§3.1 of
    the findings document). Hourly rows are averaged over each field's two-hour window, using a
    VECTOR mean so that directions either side of north average correctly.

THREE TESTS, EACH WITH A CRITERION FIXED BEFORE RUNNING

  POWER  Before any conclusion: do the 25 field times actually span a range of wind directions? If
         the wind was similar throughout, a null result means nothing and must not be reported as
         one. Require the directions to span at least 120 deg and at least 3 distinct 45 deg sectors.

  W1     IS THE SPATIAL PATTERN STATIC?  Remove each field's own spatial mean and divide by its own
         spatial standard deviation, leaving only the SHAPE. Correlate every pair of shapes.
         A mean correlation above 0.90 means the field is essentially one fixed spatial pattern
         scaled up and down by a time-varying level -- i.e. it says WHERE it is hot, not how heat
         MOVES. Criterion: mean pairwise correlation > 0.90 => pattern is static.

  W2     DOES PATTERN SIMILARITY DEPEND ON WIND DIRECTION?  For every pair of fields, compute the
         circular difference in wind direction and the shape correlation. If the field encodes wind,
         pairs with similar wind should look more alike. Criterion: Spearman rank correlation
         between direction-difference and shape-correlation more negative than -0.30 => wind
         dependence detected.

  W3     IS THE FIELD STRETCHED ALONG THE WIND?  For each field compute a directional structure
         function -- how much the temperature differs between points separated by a fixed distance,
         as a function of the direction of that separation. The direction of SMALLEST difference is
         the axis along which the field varies least, i.e. the direction it is stretched. If
         advection is present, that axis should follow the wind. Because an axis is the same at
         theta and theta+180, compare modulo 180 deg. Under no relationship the mean absolute
         difference between the two axes is 45 deg. Criterion: mean |axis - wind| < 30 deg =>
         alignment detected.

WHAT A NULL RESULT WOULD AND WOULD NOT SHOW
    A null would show that at 60 m resolution, over a 2 km window, in a two-hour maximum, we cannot
    detect wind-dependent restructuring of the field. It would NOT show that FortyGuard ignores wind
    internally -- their own description says the model is conditioned on "atmospheric, surface, and
    terrain conditions", and wind could be inside that without producing detectable advective
    structure in a two-hour maximum. That distinction must survive into anything we report to them.
"""
import sys, os, math, json, glob, statistics
import numpy as np

from common import banner, save_result, verdict, FIXTURES, SCRATCH

WIND_CSV = os.path.join(SCRATCH, "kiad_wind_2026.csv")
WIN_H = 2
LAGS_M = (200.0, 400.0, 600.0)      # separations used for the directional structure function
N_ANGLES = 12                        # 15 deg steps over 180 deg

GEOM_WARNED = []
POWER_MIN_SPAN = 120.0
POWER_MIN_SECTORS = 3
W1_STATIC = 0.90
W2_RHO = -0.30
W3_ALIGN_DEG = 30.0


# ------------------------------------------------------------------ wind
def load_wind():
    """KIAD hourly (direction deg, speed kt) keyed by (date, hour) in site-local time."""
    if not os.path.exists(WIND_CSV):
        return None
    out = {}
    for line in open(WIND_CSV, encoding="utf-8").read().splitlines()[1:]:
        p = line.split(",")
        if len(p) < 4:
            continue
        ts = p[1].strip()
        try:
            d, t = ts.split(" ")
            hh = int(t.split(":")[0])
            drct = float(p[2]); sknt = float(p[3])
        except Exception:
            continue
        out.setdefault((d, hh), []).append((drct, sknt))
    return out


def vector_mean(pairs):
    """Vector-average wind so directions either side of north combine correctly."""
    if not pairs:
        return None, None
    x = sum(s * math.sin(math.radians(d)) for d, s in pairs)
    y = sum(s * math.cos(math.radians(d)) for d, s in pairs)
    n = len(pairs)
    x /= n; y /= n
    spd = math.hypot(x, y)
    if spd < 1e-9:
        return None, 0.0
    return (math.degrees(math.atan2(x, y)) % 360.0), spd


def wind_for(wind, date, hour0):
    pairs = []
    for h in range(hour0, hour0 + WIN_H):
        pairs += wind.get((date, h), [])
    return vector_mean(pairs)


def circ_diff(a, b, mod=360.0):
    d = abs((a - b) % mod)
    return min(d, mod - d)


# ------------------------------------------------------------------ fields
def load_field(path):
    d = json.load(open(path))
    feats = (d.get("map_data") or {}).get("features") or []
    pts = []
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        v = t["properties"].get("max_temperature")
        if v is not None:
            pts.append((la, lo, v))
    return pts


def to_grid(pts):
    """Put the tiles on their own lattice using TILE ORDER; returns (Z, dy_m, dx_m, rot_deg).

    🐛 BUG FIXED 2026-08-12. The first version inferred the lattice from distinct latitude and
    longitude values. That silently produced a 397 x 397 array holding only 397 values, with 2.8 m
    "cells", because THE FORTYGUARD TILE LATTICE IS ROTATED relative to lat/lon: stepping one tile
    east also moves you about 2.7 m north, so no two tiles in a row share a latitude and no two in a
    column share a longitude.

        tile 0 -> tile 1  (same row)   : +101.1 m east, +2.7 m north
        tile 0 -> tile 20 (next row)   : -2.7 m east, +101.0 m north
        => a regular ~101 m grid rotated about 1.55 deg from north

    Value-matched analyses (the SVD, and the pairwise shape correlations) were unaffected, because
    they only ever compare like position with like position and never use spatial arrangement. Any
    analysis needing real neighbours -- the directional structure function -- was invalid.

    The fix uses the response's own row-major tile ORDER, detecting the row length from where the
    longitude stops increasing. The 1.55 deg rotation is left uncorrected: it is far below the 15 deg
    angular resolution of the structure function, and treating it as zero is stated rather than
    hidden.
    """
    # row length = first index where longitude stops increasing
    ncols = None
    for k in range(1, len(pts)):
        if pts[k][1] < pts[k - 1][1]:
            ncols = k
            break
    if ncols is None or ncols < 2:
        raise ValueError("could not detect the tile row length from ordering")
    nrows = int(math.ceil(len(pts) / ncols))
    Z = np.full((nrows, ncols), np.nan)
    for k, (la, lo, v) in enumerate(pts):
        Z[k // ncols, k % ncols] = v

    mlat = statistics.fmean(p[0] for p in pts)
    kx = 111320.0 * math.cos(math.radians(mlat))
    # along-row step (tile 0 -> 1) and along-column step (tile 0 -> ncols)
    ex = (pts[1][1] - pts[0][1]) * kx
    ey = (pts[1][0] - pts[0][0]) * 111320.0
    cx = (pts[ncols][1] - pts[0][1]) * kx
    cy = (pts[ncols][0] - pts[0][0]) * 111320.0
    dx = math.hypot(ex, ey)          # metres per column step
    dy = math.hypot(cx, cy)          # metres per row step
    rot = math.degrees(math.atan2(ey, ex))

    # Refuse to return a reconstruction we cannot trust. The AOI is a POLYGON, so rows can be
    # ragged, and "first longitude decrease" then finds a row break that is not the row length --
    # on the 2 km fields it returns 13 columns where the geometry says 20, giving 715 m "rows"
    # against 101 m columns. A square tiling must give near-equal steps, so that is the check.
    # Failing loudly here is the point: the earlier version silently produced a 397 x 397 array
    # with 2.8 m cells and a downstream test then reported a confident, meaningless number.
    if not (0.75 < dx / dy < 1.33):
        raise ValueError(
            "tile lattice reconstruction failed: %d x %d with %.1f m columns and %.1f m rows "
            "(ratio %.2f). Row-major ordering could not be recovered from a polygon AOI. Any "
            "analysis needing real neighbours must be skipped."
            % (Z.shape[0], Z.shape[1], dx, dy, dx / dy))
    return Z, dy, dx, rot


def shape(Z):
    """Remove the field's own mean and sd, leaving only spatial SHAPE."""
    v = Z[np.isfinite(Z)]
    m, s = float(v.mean()), float(v.std())
    if s < 1e-9:
        return None
    return (Z - m) / s


def _bilinear(Z, fi, fj):
    """Sample Z at fractional row/col offsets by bilinear interpolation. NaN outside or near NaN.

    🐛 BUG FIXED 2026-08-12. The first version of this function converted the lag to INTEGER cell
    offsets with round(). At 100 m cells and a requested 200 m lag that makes the ACTUAL separation
    vary from 141 m (at 45 deg, offsets 1,1) to 224 m (at 15 deg, offsets 2,1) depending on the
    angle. A shorter actual separation gives a smaller temperature difference, so the angle with the
    unluckiest rounding won every time -- the test returned 30 deg for all 25 fields, which is the
    signature of an artifact, not a measurement. Interpolating at the exact fractional offset keeps
    the separation identical at every angle, which is the only way the comparison means anything.
    """
    ni, nj = Z.shape
    i0 = np.floor(fi).astype(int); j0 = np.floor(fj).astype(int)
    di = fi - i0; dj = fj - j0
    ok = (i0 >= 0) & (j0 >= 0) & (i0 + 1 < ni) & (j0 + 1 < nj)
    out = np.full(fi.shape, np.nan)
    if not ok.any():
        return out
    ii0 = i0[ok]; jj0 = j0[ok]; a = di[ok]; b = dj[ok]
    v = (Z[ii0, jj0] * (1 - a) * (1 - b) + Z[ii0 + 1, jj0] * a * (1 - b)
         + Z[ii0, jj0 + 1] * (1 - a) * b + Z[ii0 + 1, jj0 + 1] * a * b)
    out[ok] = v
    return out


def struct_axis(Z, dy, dx):
    """Direction (deg from north, mod 180) of SMALLEST temperature difference at FIXED separation.

    gamma(theta) = mean over the field of (T(p) - T(p + h*unit(theta)))^2, the second point sampled
    by bilinear interpolation so that |separation| = h exactly at every angle. The minimising
    direction is the axis along which the field varies least -- its stretching axis.
    """
    ni, nj = Z.shape
    I, J = np.meshgrid(np.arange(ni, dtype=float), np.arange(nj, dtype=float), indexing="ij")
    best = (None, float("inf"))
    per = {}
    for a in range(N_ANGLES):
        th = 180.0 * a / N_ANGLES
        acc, cnt = 0.0, 0
        for h in LAGS_M:
            fi = I + h * math.cos(math.radians(th)) / dy
            fj = J + h * math.sin(math.radians(th)) / dx
            B = _bilinear(Z, fi, fj)
            m = np.isfinite(Z) & np.isfinite(B)
            if m.sum() < 30:
                continue
            acc += float(((Z[m] - B[m]) ** 2).mean()); cnt += 1
        if cnt:
            g = acc / cnt
            per[th] = g
            if g < best[1]:
                best = (th, g)
    return best[0], per


def single_template_svd(Zs):
    """Do all these fields reduce to ONE fixed spatial pattern, scaled and offset?

    Remove each field's own spatial MEAN (so a uniform offset is free) but keep its amplitude, then
    take the SVD across fields. If component 1 explains essentially all the spatial variance, the
    product is delivering one template multiplied by a single time-varying number -- which means the
    tile count overstates how much independent spatial information is present.
    """
    mask = np.ones_like(Zs[0], dtype=bool)
    for Z in Zs:
        mask &= np.isfinite(Z)
    X = np.array([Z[mask] for Z in Zs])
    Xc = X - X.mean(axis=1, keepdims=True)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = (S ** 2) / (S ** 2).sum()
    resid = Xc - np.outer(U[:, 0] * S[0], Vt[0])
    return {"n_pixels": int(mask.sum()),
            "var_explained": [float(v) for v in var[:6]],
            "amplitudes": [float(x) for x in (U[:, 0] * S[0])],
            "resid_rms": float(np.sqrt((resid ** 2).mean())),
            "orig_rms": float(np.sqrt((Xc ** 2).mean()))}


def spearman(x, y):
    def rank(v):
        o = np.argsort(np.asarray(v, dtype=float))
        r = np.empty(len(v)); r[o] = np.arange(len(v), dtype=float)
        return r
    rx, ry = rank(x), rank(y)
    rx -= rx.mean(); ry -= ry.mean()
    den = math.sqrt(float((rx ** 2).sum()) * float((ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den > 0 else 0.0


# ------------------------------------------------------------------ main
def main():
    banner("N-31  Does FortyGuard's 60 m field contain wind-dependent structure?   [FREE]")
    wind = load_wind()
    if wind is None:
        print("   KIAD wind file not found at %s" % WIND_CSV)
        print("   fetch it from the Iowa State ASOS archive first.")
        return 2

    paths = sorted(glob.glob(os.path.join(FIXTURES, "n12c_*.json")))
    recs = []
    for p in paths:
        b = os.path.basename(p)
        date = b.split("_")[1]
        hour0 = int(b.split("_")[2].split(".")[0][:2])
        wd, ws = wind_for(wind, date, hour0)
        if wd is None:
            print("   no usable wind for %s %02d:00 -- skipped" % (date, hour0))
            continue
        pts = load_field(p)
        try:
            Z, dy, dx, rot = to_grid(pts)
        except ValueError as e:
            # Geometry-independent analyses (W0/W1/W2) still work: they compare like position with
            # like position and never use neighbours. Lay the values out in a stable order.
            Z = np.array([v for _, _, v in sorted(pts, key=lambda r: (r[0], r[1]))],
                         dtype=float).reshape(1, -1)
            dy = dx = rot = float("nan")
            if not GEOM_WARNED:
                print("   WARNING: %s" % str(e))
                print("      -> W3 (needs real neighbours) will be SKIPPED. W0/W1/W2 are")
                print("         value-matched and unaffected.")
                GEOM_WARNED.append(1)
        S = shape(Z)
        if S is None:
            continue
        recs.append({"file": b, "date": date, "hour": hour0, "wind_dir": wd, "wind_kt": ws,
                     "Z": Z, "S": S, "dy": dy, "dx": dx, "rot_deg": rot, "n": len(pts)})

    print("\n   %d fields matched to concurrent KIAD wind" % len(recs))
    geom_ok = math.isfinite(recs[0]["dx"])
    if geom_ok:
        print("   tile lattice %d x %d, %.1f x %.1f m cells, rotated %+.2f deg from due east"
              % (recs[0]["Z"].shape[0], recs[0]["Z"].shape[1], recs[0]["dy"], recs[0]["dx"],
                 recs[0]["rot_deg"]))
    print("\n   %-12s %6s %10s %9s %11s %11s"
          % ("date", "hour", "wind from", "wind kt", "field mean", "field sd"))
    for r in recs:
        v = r["Z"][np.isfinite(r["Z"])]
        print("   %-12s %6s %10.0f %9.1f %11.3f %11.4f"
              % (r["date"], "%02d:00" % r["hour"], r["wind_dir"], r["wind_kt"], v.mean(), v.std()))

    # ---------------- POWER ----------------
    dirs = [r["wind_dir"] for r in recs]
    sectors = sorted(set(int(d // 45) for d in dirs))
    span = max(circ_diff(a, b) for a in dirs for b in dirs)
    print("\n   POWER CHECK  (before any conclusion is allowed)")
    print("      wind directions observed : %s" % ", ".join("%.0f" % d for d in sorted(dirs)))
    print("      distinct 45 deg sectors  : %d  %s" % (len(sectors), sectors))
    print("      maximum angular span     : %.0f deg" % span)
    power = span >= POWER_MIN_SPAN and len(sectors) >= POWER_MIN_SECTORS
    print("      sufficient spread to detect wind dependence (>= %.0f deg, >= %d sectors): %s"
          % (POWER_MIN_SPAN, POWER_MIN_SECTORS, power))
    if not power:
        print("\n      *** The wind barely varied across these fields. A null result here would be")
        print("          meaningless and MUST NOT be reported as evidence of anything. Collect")
        print("          fields spanning more wind directions before concluding.")

    # ---------------- W0: the decisive analysis ----------------
    print("\n   W0  DO ALL %d FIELDS REDUCE TO ONE FIXED SPATIAL TEMPLATE?  (SVD)" % len(recs))
    sv = single_template_svd([r["Z"] for r in recs])
    print("      %d common pixels. Spatial variance explained, by component:" % sv["n_pixels"])
    for k, v in enumerate(sv["var_explained"]):
        print("         component %d : %8.4f %%" % (k + 1, 100 * v))
    print("      removing component 1 alone leaves residual rms %.6f C, from %.6f C"
          % (sv["resid_rms"], sv["orig_rms"]))
    one_template = sv["var_explained"][0] > 0.99
    print("      component 1 > 99 %%  =>  ONE template + one scalar + one offset : %s" % one_template)
    if one_template:
        print("      Consequence for a client: these %d tiles carry only TWO degrees of freedom"
              % recs[0]["n"])
        print("      beyond a fixed pattern (an amplitude and an offset). The tile count overstates")
        print("      how much independent spatial information is present. And a plume cannot be in")
        print("      here at all -- there is no spatial degree of freedom left for it to occupy.")
        amps = sv["amplitudes"]
        if min(amps) < 0 < max(amps):
            print("      NOTE: the amplitude CHANGES SIGN across these fields (%+.3f to %+.3f), so the"
                  % (min(amps), max(amps)))
            print("      pattern inverts exactly between some consecutive windows.")

    # ---------------- W1 ----------------
    print("\n   W1  IS THE SPATIAL PATTERN STATIC?")
    pair_corr, pair_dd, pairs = [], [], []
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            A, B = recs[i]["S"], recs[j]["S"]
            m = np.isfinite(A) & np.isfinite(B)
            if m.sum() < 50:
                continue
            c = float(np.corrcoef(A[m], B[m])[0, 1])
            dd = circ_diff(recs[i]["wind_dir"], recs[j]["wind_dir"])
            pair_corr.append(c); pair_dd.append(dd)
            pairs.append((recs[i]["file"], recs[j]["file"], c, dd))
    pc = np.array(pair_corr)
    print("      %d field pairs. shape correlation: mean %.4f, min %.4f, max %.4f"
          % (len(pc), pc.mean(), pc.min(), pc.max()))
    w1_static = bool(pc.mean() > W1_STATIC)
    print("      mean > %.2f  =>  field is essentially ONE fixed spatial pattern : %s"
          % (W1_STATIC, w1_static))
    if w1_static:
        print("      Interpretation: the 60 m field tells you WHERE it is hot. Between these")
        print("      %d observations the shape barely changes -- only the overall level does." % len(recs))

    # ---------------- W2 ----------------
    rho = spearman(pair_dd, pair_corr)
    print("\n   W2  DOES PATTERN SIMILARITY DEPEND ON WIND DIRECTION?")
    print("      Spearman(direction difference, shape correlation) = %+.4f" % rho)
    bins = [(0, 30), (30, 60), (60, 90), (90, 135), (135, 180)]
    print("      %-14s %8s %12s" % ("dir diff", "pairs", "mean corr"))
    for lo, hi in bins:
        sel = [c for c, d in zip(pair_corr, pair_dd) if lo <= d < hi]
        if sel:
            print("      %-14s %8d %12.4f" % ("%d-%d deg" % (lo, hi), len(sel), statistics.fmean(sel)))
    w2_wind = bool(rho < W2_RHO)
    print("      rho < %.2f  =>  wind dependence detected : %s" % (W2_RHO, w2_wind))

    # ---------------- W3 ----------------
    print("\n   W3  IS THE FIELD STRETCHED ALONG THE WIND?")
    print("      %-12s %6s %10s %12s %12s"
          % ("date", "hour", "wind from", "stretch axis", "|diff| mod 180"))
    diffs = []
    if not geom_ok:
        print("      SKIPPED - the tile lattice could not be reconstructed (warning above).")
        print("      Reporting no number is the correct outcome. An earlier version of this test")
        print("      reported 30 deg for all 25 fields, which was purely a rounding artifact.")
    for r in (recs if geom_ok else []):
        ax, per = struct_axis(r["S"], r["dy"], r["dx"])
        if ax is None:
            continue
        d = circ_diff(ax, r["wind_dir"] % 180.0, mod=180.0)
        diffs.append(d)
        r["axis"] = ax; r["axis_diff"] = d
        print("      %-12s %6s %10.0f %12.0f %12.0f"
              % (r["date"], "%02d:00" % r["hour"], r["wind_dir"], ax, d))
    md = statistics.fmean(diffs) if diffs else float("nan")
    print("      mean |stretch axis - wind| = %.1f deg   (45 deg = no relationship)" % md)
    w3_align = bool(md < W3_ALIGN_DEG)
    print("      < %.0f deg  =>  alignment detected : %s" % (W3_ALIGN_DEG, w3_align))

    # ---------------- verdict ----------------
    detected = w2_wind or w3_align
    print("\n   RESULT")
    print("      power sufficient                        : %s" % power)
    print("      W1 pattern is static                    : %s (mean corr %.4f)" % (w1_static, pc.mean()))
    print("      W2 similarity depends on wind direction : %s (rho %+.4f)" % (w2_wind, rho))
    print("      W3 field stretched along the wind       : %s (mean |diff| %.1f deg)" % (w3_align, md))
    print("      -> wind-dependent structure DETECTED    : %s" % detected)

    print("\n   WHAT THIS DOES AND DOES NOT LICENCE")
    if not power:
        print("      Nothing. The wind did not vary enough. Do not report a null.")
    elif detected:
        print("      Wind-dependent structure IS present. We must check for DOUBLE-COUNTING before")
        print("      adding our own plume on top, and the feature request below is NOT warranted.")
    else:
        print("      At 60 m resolution, over a 2 km window, in a two-hour maximum, and across")
        print("      %.0f deg of wind direction, we cannot detect wind-dependent restructuring." % span)
        print("      LICENSED:   'we found no detectable advective structure, so our plume is")
        print("                   additive rather than double-counted'")
        print("      NOT LICENSED: 'FortyGuard ignores wind'. Their own description says the model")
        print("                   is conditioned on atmospheric conditions, and wind may be inside")
        print("                   that without producing detectable structure in a 2 h maximum.")
        print("      The DEFENSIBLE request is the plain verifiable fact: wind is not EXPOSED in")
        print("      any response field, so a client cannot obtain it from FortyGuard at all.")

    ok = bool(power)
    print()
    verdict(ok,
            "CONCLUSIVE - the wind spanned %.0f deg across %d distinct sectors, so the test had the "
            "power to detect wind dependence. Result: %s. Mean pairwise shape correlation %.4f."
            % (span, len(sectors), "DETECTED" if detected else "NOT detected", pc.mean()),
            "INCONCLUSIVE - the wind varied by only %.0f deg across %d sectors, below the "
            "pre-registered %.0f deg / %d sectors needed. Whatever the other numbers say, this "
            "cannot support a claim in either direction. Collect fields spanning more wind "
            "directions." % (span, len(sectors), POWER_MIN_SPAN, POWER_MIN_SECTORS))

    save_result("n31_windalign.json", {
        "question": "does the 60 m field contain wind-dependent spatial structure?",
        "svd_single_template": sv, "one_template": one_template,
        "no_new_api_calls": True,
        "wind_source": "KIAD ASOS via Iowa State Environmental Mesonet, America/New_York, "
                       "vector-averaged over each 2 h window",
        "n_fields": len(recs), "grid": list(recs[0]["Z"].shape),
        "cell_m": [recs[0]["dy"], recs[0]["dx"]],
        "fields": [{k: r[k] for k in ("file", "date", "hour", "wind_dir", "wind_kt", "n")
                    if k in r} for r in recs],
        "wind_dirs": dirs, "wind_span_deg": span, "n_sectors": len(sectors), "power": power,
        "n_pairs": len(pc), "mean_pair_corr": float(pc.mean()),
        "min_pair_corr": float(pc.min()), "max_pair_corr": float(pc.max()),
        "w1_pattern_static": w1_static, "w1_threshold": W1_STATIC,
        "spearman_dirdiff_vs_corr": rho, "w2_wind_dependence": w2_wind, "w2_threshold": W2_RHO,
        "axis_diffs_deg": diffs, "mean_axis_diff_deg": md,
        "w3_alignment": w3_align, "w3_threshold_deg": W3_ALIGN_DEG,
        "wind_structure_detected": detected,
        "licensed_claim": "no detectable advective structure at this resolution/averaging; our "
                          "plume is additive" if (power and not detected) else None,
        "not_licensed": "that FortyGuard ignores wind internally",
        "pass": ok})
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
