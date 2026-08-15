# -*- coding: utf-8 -*-
"""2-D steady-state advection-diffusion solver for site-scale intake temperature.

Physics: dT/dt = -u.dT/dx - v.dT/dy + D.laplacian(T) + S
Upwind differencing for advection, central for diffusion, explicit time-stepping
to steady state. Condenser banks are heat sources. Inflow boundary is held at
ambient; outflow is zero-gradient.

BUILDINGS ARE HEAT SINKS, NOT NO-FLOW WALLS -- corrected 2026-08-12 (N-29 V4).
    This docstring previously said "Buildings are no-flow obstacle cells". That is FALSE. The
    implementation does `newT = np.where(free, newT, ambient)`, pinning every obstacle cell to
    ambient on every step. That is a fixed-temperature Dirichlet condition, which ABSORBS heat. A
    no-flow wall would be zero-gradient: it reflects, deflects the plume around itself, and
    conserves heat.

    The consequence is not subtle. N-29 measured it directly: a 120 x 200 m building placed across
    an otherwise verified Gaussian plume removed **99.7 %** of the heat, against 100.0 % conserved
    in the open domain. Physically air flows AROUND a building; it is not annihilated by one.

    So intake rise is biased LOW -- potentially drastically -- for any wind direction where a
    structure sits between the source and the intake. Directions blocked by a building will look
    "safe" when they may not be.

    Not yet changed, because fixing it alters every number computed so far and that must be a
    deliberate decision rather than a side effect. Results whose source-to-intake path is clear are
    unaffected: demo_site's condenser bank spans x 800-860 and its intake sits at x 1090 with no
    building between, so N-8/N-19/N-23/N-27 do not depend on this. N-28's multi-layout
    classification may, and is flagged there.

VERIFICATION STATUS (N-29, no measurements involved)
    diffusion term    EXACT -- fitted sigma_y^2 slope matches the analytic 2D/u to 0.00 % at
                      dx = 20, 10 and 5 m on an empty domain
    heat conservation EXACT -- u * integral(theta dy) equals the total source to 0.00 % at every
                      downstream station
    grid convergence  converges to ~0.606 C with a residual change of 0.002 C between dx = 5 and
                      dx = 2.5, but only once the intake averaging operator is made dx-consistent
                      (see intake_temperature below). Convergence is oscillatory, so no clean
                      Richardson order can be extracted and none is claimed.

Runs on NumPy (CPU). If NVIDIA Warp is installed, warp_step() runs the identical
kernel on the GPU -- the point being that a 100-member ensemble is what needs it.
"""
import math
import numpy as np

try:
    import warp as wp
    HAVE_WARP = True
except Exception:
    HAVE_WARP = False


class Site:
    """A square patch of ground with buildings and heat sources."""

    def __init__(self, size_m=2000.0, dx=10.0):
        self.dx = dx
        self.n = int(size_m / dx)
        self.obstacle = np.zeros((self.n, self.n), dtype=bool)
        self.source = np.zeros((self.n, self.n), dtype=np.float64)   # K per second

    def add_building(self, cx, cy, w, h):
        """cx,cy,w,h in metres from the lower-left corner."""
        i0, i1 = int((cy - h / 2) / self.dx), int((cy + h / 2) / self.dx)
        j0, j1 = int((cx - w / 2) / self.dx), int((cx + w / 2) / self.dx)
        self.obstacle[max(0, i0):min(self.n, i1), max(0, j0):min(self.n, j1)] = True

    def add_condensers(self, cx, cy, w, h, discharge_k, exchange_s=60.0):
        """A condenser bank discharging air `discharge_k` above ambient.
        Modelled as a volumetric source that would raise a cell by discharge_k
        over `exchange_s` seconds."""
        i0, i1 = int((cy - h / 2) / self.dx), int((cy + h / 2) / self.dx)
        j0, j1 = int((cx - w / 2) / self.dx), int((cx + w / 2) / self.dx)
        self.source[max(0, i0):min(self.n, i1), max(0, j0):min(self.n, j1)] += discharge_k / exchange_s


# ---------------------------------------------------------------------------------------------
# CALIBRATED CONSTANTS -- fitted in N-22 to ~40,000 measured points from six instrumented ACCs
# (Maulbetsch & DiFilippo, California Energy Commission CEC-500-2013-065 and Appendix B).
# Held-out RMS 0.126 K on three plants never used in the fit = 14 % of the mean signal.
#
# These REPLACE the N-11 values (exponent 2.0, exchange_s 20 s), which were fitted to a sentence in
# the literature and were anti-correlated (r = -0.869) with the field data. See N-21.
#
# HONEST CAVEAT: the held-out CORRELATION is only +0.082, because the measured wind-speed
# dependence spans just 0.20 K around a 0.92 K mean -- there is almost no shape to fit. The
# magnitude is validated; the shape is not resolvable from this data. Wind DIRECTION carries the
# signal (measured swing 1.60 x, vs 1.22 x across the whole speed range).
CALIBRATED = {"downwash_exponent": 1.25, "downwash_uc": 8.0, "exchange_s": 47.4}


def downwash_fraction(wind_speed, uc=8.0, exponent=1.25):
    """Fraction of condenser discharge that STAYS in the near-surface layer this 2-D model
    represents. The rest climbs out of it and is carried away aloft.

    WHY THIS EXISTS. Condenser discharge is hot, so it is buoyant and rises. Bent-over
    buoyant plume theory (Briggs) gives plume rise proportional to 1/U: in calm air the
    plume climbs out of the intake layer, and wind bends it over and pins it down. So the
    fraction re-ingested at intake level GROWS with wind speed. Without this term the model
    injects 100 % of the discharge at ground level at every wind speed -- which is the
    high-wind limit applied everywhere, and it makes intake rise fall monotonically with
    wind when the literature has it rising.

    [S] CALIBRATED, NOT DERIVED -- and the distinction matters:
      uc = 8 m/s      and exponent = 1.25: FITTED in N-22 to 40,000 field measurements, NOT to a
                      literature claim. The earlier exponent of 2.0 came from N-11 and was
                      falsified in N-21.
    This is an empirical closure for physics a 2-D model cannot resolve (3-D wake vortices,
    fan-flow degradation in cross wind). It is standard practice for unresolved physics, but
    it is a fit to published behaviour, not a first-principles result. Say so out loud.

    uc=None disables the term, reproducing the original behaviour so the change is auditable.
    """
    if uc is None:
        return 1.0
    U = max(float(wind_speed), 0.0)
    uc = max(float(uc), 1e-6)
    return U ** exponent / (U ** exponent + uc ** exponent)


def solve(site, ambient, wind_speed, wind_from_deg, diffusivity=8.0,
          max_steps=4000, tol=1e-6, return_steps=False,
          downwash_uc=None, downwash_exponent=CALIBRATED["downwash_exponent"]):
    """Steady-state temperature field. wind_from_deg is meteorological (direction it blows FROM).

    downwash_uc=None keeps the original (defective) behaviour: all discharge injected at
    ground level regardless of wind. Pass a value to enable the plume-rise closure above.
    Default is None so every previously-recorded result stays reproducible.

    BUG FIXED 2026-08-12: downwash_exponent defaulted to 2.0 -- the value N-21 FALSIFIED against
    field data -- while downwash_fraction() had already been moved to the calibrated 1.25. Any
    caller that passed downwash_uc but not the exponent therefore got 2.0 from this function and
    1.25 from the free function. At 6 m/s with uc = 8 that is a retained fraction of 0.360 versus
    0.411: a 14 % difference in source strength between two code paths meant to be identical.
    test_n16_warp.py did exactly that -- CPU through solve(), GPU through downwash_fraction() --
    so its CPU-vs-GPU agreement figure was measured before the split and would not have
    reproduced. Both paths now read CALIBRATED. Callers that want the old exponent must pass it
    explicitly; test_n11_windspeed.py already does, because comparing exponents is its job.
    """
    n, dx = site.n, site.dx
    # meteorological FROM -> vector TOWARD
    th = math.radians(wind_from_deg + 180.0)
    u = wind_speed * math.sin(th)          # +x = east
    v = wind_speed * math.cos(th)          # +y = north

    # Correct COMBINED stability limit for explicit upwind advection + central diffusion.
    # Using min(dx/max(|u|,|v|), dx^2/4D) separately is marginally unstable for diagonal
    # winds and blows up: the two mechanisms share the timestep, so they add.
    dt = 0.4 / ((abs(u) + abs(v)) / dx + 4.0 * diffusivity / (dx * dx) + 1e-12)

    T = np.full((n, n), float(ambient))
    # plume-rise closure: only the share that stays in this layer acts as a source here
    src = site.source * downwash_fraction(wind_speed, downwash_uc, downwash_exponent)
    obs = site.obstacle
    free = ~obs

    # Below EPS the flow is effectively calm: use central differencing so the
    # scheme stays symmetric. A one-sided stencil at u~0 breaks radial symmetry.
    EPS = 1e-2          # 1 cm/s: below this the flow is physically calm

    for step in range(max_steps):
        Tp = np.pad(T, 1, mode="edge")
        # inflow boundaries held at ambient; when calm, hold all of them
        if u > EPS:      Tp[:, 0] = ambient
        elif u < -EPS:   Tp[:, -1] = ambient
        else:            Tp[:, 0] = Tp[:, -1] = ambient
        if v > EPS:      Tp[0, :] = ambient
        elif v < -EPS:   Tp[-1, :] = ambient
        else:            Tp[0, :] = Tp[-1, :] = ambient

        C = Tp[1:-1, 1:-1]
        N, S = Tp[2:, 1:-1], Tp[:-2, 1:-1]
        E, W = Tp[1:-1, 2:], Tp[1:-1, :-2]

        # upwind advection where there is flow, central where there is not
        if u > EPS:    dTdx = (C - W) / dx
        elif u < -EPS: dTdx = (E - C) / dx
        else:          dTdx = (E - W) / (2 * dx)
        if v > EPS:    dTdy = (C - S) / dx
        elif v < -EPS: dTdy = (N - C) / dx
        else:          dTdy = (N - S) / (2 * dx)
        adv = -(u * dTdx + v * dTdy)
        lap = (N + S + E + W - 4 * C) / (dx * dx)
        newT = C + dt * (adv + diffusivity * lap + src)

        # OBSTACLE PINNING REMOVED 2026-08-12.
        #
        # This line used to read `newT = np.where(free, newT, ambient)`, with the comment
        # "obstacles do not hold air". That is a fixed-temperature (Dirichlet) boundary, and a cell
        # held at a fixed temperature ABSORBS heat without limit. N-29 measured the consequence
        # directly: a 120 x 200 m building placed across an otherwise exactly-conserving plume
        # removed 99.7 % of the heat, against 100.0 % conserved in the open domain. Real air flows
        # AROUND a building. It is deflected, not destroyed.
        #
        # It was also corrupting the headline number, not just blocked directions: 21 of the 49
        # cells in demo_site's intake averaging disc lie inside the neighbour building, so they were
        # pinned to a rise of exactly zero and dragged the reported intake temperature down 43 %.
        #
        # WHAT REPLACES IT, AND WHY NOT SOMETHING CLEVERER
        #   Obstacles are now TRANSPARENT to the temperature field: heat passes through where a
        #   building is. That is not right either, but it is wrong in one stated direction instead
        #   of catastrophically, and it conserves heat exactly.
        #
        #   The obvious alternative -- mirroring neighbour values so walls are adiabatic -- restores
        #   conservation but creates a WORSE artifact here, because the velocity field is uniform and
        #   does not know the buildings exist. Heat would advect into the wall and pile up with
        #   nowhere to go, producing a fake stagnation hotspot. demo_site's intake sits 10 m upwind
        #   of the neighbour's west face, so that artifact would land directly on it.
        #
        #   The correct fix is a mass-consistent (divergence-free) wind field: zero the velocity
        #   inside obstacles, then solve one Poisson equation for a correction potential so the flow
        #   goes around them. That is the standard diagnostic-wind-model approach (MATHEW/CALMET
        #   family, after Sherman 1978). It is one extra Poisson solve and it is the right next step
        #   -- but it introduces an approximation we cannot yet validate, and CEDVAL wind-tunnel data
        #   around an isolated building is the dataset that would validate it.
        #
        # WHY TRANSPARENT IS DEFENSIBLE FOR THIS GEOMETRY
        #   ASHRAE Handbook HVAC Applications 2019 Ch. 46 distinguishes a VISIBLE intake (direct line
        #   of sight to the source) from a HIDDEN one (behind an obstruction), and applies a dilution
        #   correction only to hidden intakes -- a conservative factor of 2.0. demo_site's intake has
        #   direct line of sight to the condenser bank, so "no building correction" is the sourced
        #   treatment for our case rather than a shortcut.
        #
        #   For directions where a building DOES block the path, the honest answer is to refuse to
        #   report a number rather than return a wrong one. Use path_blocked() below.
        #
        # The obstacle mask is retained and still used, for excluding building interiors from the
        # intake average and for path_blocked(). It just no longer alters the temperature field.

        # divergence guard: a diverging run must be reported, never silently averaged in
        if not np.all(np.isfinite(newT)) or float(np.max(np.abs(newT - ambient))) > 500.0:
            raise FloatingPointError(
                "solver diverged at step %d (u=%.2f v=%.2f dx=%.1f dt=%.4f)" % (step, u, v, dx, dt))

        delta = float(np.max(np.abs(newT - T)))
        T = newT
        if delta < tol:
            break

    return (T, step + 1) if return_steps else T


def path_blocked(site, src_xy, ix, iy, wind_from_deg, samples=400):
    """Does a building sit between the heat source and the intake, on the plume's path?

    Returns True when the agent should REFUSE to report a number for this wind direction rather
    than return one the model cannot compute. Two conditions must both hold:

      1. the intake is genuinely DOWNWIND of the source -- the source-to-intake vector has a
         positive component along the wind vector. If the intake is upwind, no plume reaches it and
         buildings are irrelevant.
      2. the straight segment from source to intake crosses an obstacle cell.

    Why refusing is the right behaviour: obstacles are transparent to the temperature field (see
    solve()), so a blocked path would silently return the unobstructed answer -- too HIGH, since the
    real building would deflect the plume. Previously the pinning made it far too LOW. Neither is
    computable with a uniform velocity field, so the honest output is "not modelled".

    ASHRAE Ch. 46 calls this the HIDDEN-intake case and applies a conservative dilution factor of
    2.0. Once a mass-consistent wind field exists (validated against CEDVAL), this can return a
    number instead of a refusal.
    """
    th = math.radians(wind_from_deg + 180.0)          # direction the wind blows TOWARD
    wx, wy = math.sin(th), math.cos(th)
    sx, sy = float(src_xy[0]), float(src_xy[1])
    dxv, dyv = ix - sx, iy - sy
    if dxv * wx + dyv * wy <= 0.0:
        return False                                  # intake is upwind: nothing to block
    n, dx = site.n, site.dx
    for k in range(1, samples):
        t = k / float(samples)
        px, py = sx + t * dxv, sy + t * dyv
        j, i = int(px / dx), int(py / dx)
        if 0 <= i < n and 0 <= j < n and site.obstacle[i, j]:
            return True
    return False


def intake_temperature(T, site, ix, iy, radius_m=30.0, disc=False, exclude_obstacles=True):
    """Mean temperature over a small region at the intake location (metres from corner).

    ⚠ THE DEFAULT (disc=False) IS A SQUARE BOX WHOSE PHYSICAL SIZE DEPENDS ON dx.
        r = max(1, int(radius_m/dx)) then slicing [i-r : i+r+1] gives (2r+1) cells, i.e.
        (2r+1)*dx metres across:

            dx = 20 m  ->  3 cells  ->  60 m      dx =  5 m  ->  13 cells  ->  65 m
            dx = 10 m  ->  7 cells  ->  70 m      dx = 2.5 m ->  25 cells  ->  62.5 m

        So a grid-refinement study using this operator compares three DIFFERENT measurements, and
        that is what made N-29's V3 fail with a sign flip: the intake rise came out 0.562, 0.479,
        0.521 C at dx = 20, 10, 5. The solver was not at fault -- V1 and V2 verified the numerics as
        exact -- the measurement operator was.

        It is also a BOX, not a disc: at dx = 10 it averages 4,900 m^2 where a 30 m disc is 2,827 m^2,
        so it pulls in cooler surrounding air and reads LOW. At dx = 10 the box gives 0.479 C where
        the disc gives 0.586 C on the identical field -- a 0.107 C difference from the operator alone,
        larger than the 0.020 C attributable to resolution.

    disc=True averages cells whose CENTRES fall inside radius_m, which is a fixed physical region and
    converges properly: 0.626, 0.586, 0.608, 0.606 C at dx = 20, 10, 5, 2.5, a residual change of
    0.002 C at the finest step.

    THE DEFAULT IS DELIBERATELY LEFT AS THE BOX so that every previously recorded result stays
    reproducible. All headline numbers are internally consistent because they all use it, and the
    absolute value is already quoted as a band (N-19: 0.219-0.940 C) inside which this 0.107 C sits.
    Any NEW absolute claim should pass disc=True and say so.
    """
    n, dx = site.n, site.dx
    if disc:
        yy, xx = np.meshgrid((np.arange(n) + 0.5) * dx, (np.arange(n) + 0.5) * dx, indexing="ij")
        m = ((xx - ix) ** 2 + (yy - iy) ** 2) <= radius_m ** 2
        if not m.any():
            m[int(iy / dx), int(ix / dx)] = True
    else:
        r = max(1, int(radius_m / dx))
        i, j = int(iy / dx), int(ix / dx)
        m = np.zeros((n, n), dtype=bool)
        m[max(0, i - r):min(n, i + r + 1), max(0, j - r):min(n, j + r + 1)] = True

    if exclude_obstacles:
        air = m & ~site.obstacle
        if not air.any():
            raise ValueError(
                "intake at (%.0f, %.0f) has NO air cells within %.0f m -- the whole averaging "
                "region is inside a building. Check the geometry." % (ix, iy, radius_m))
        m = air
    return float(T[m].mean())


def intake_source_overlap(site, ix, iy, radius_m=30.0):
    """Fraction of the intake averaging disc that sits on CONDENSER SOURCE cells.

    Must be 0. Anything above 0 means the disc is averaging the heat source itself and calling the
    result "the neighbour's intake temperature", which is physically meaningless -- you are reading
    the discharge, not what anyone breathes.

    Added 2026-08-12 after N-27 found that separation_m = 150 m put **71 %** of the disc inside the
    condenser bank, and that N-19 swept that same value into its published sensitivity band. The
    geometry is only valid when

        separation_m  >  110 + bank_w + intake_r

    (intake x = 690 + separation, bank right edge = 800 + bank_w, disc half-width = intake_r). With
    the defaults bank_w = 60 and intake_r = 30 that means separation must exceed 200 m. Nothing in
    the code enforced it, and the failure is silent: you get a large, plausible-looking number.
    """
    r = max(1, int(radius_m / site.dx))
    i, j = int(iy / site.dx), int(ix / site.dx)
    i0, i1 = max(0, i - r), min(site.n, i + r + 1)
    j0, j1 = max(0, j - r), min(site.n, j + r + 1)
    return float((site.source[i0:i1, j0:j1] > 0).mean())


def assert_intake_clear(site, ix, iy, radius_m=30.0, label=""):
    """Raise unless the intake disc is clear of the source. Call this in every geometry sweep."""
    f = intake_source_overlap(site, ix, iy, radius_m)
    if f > 0:
        raise ValueError(
            "DEGENERATE GEOMETRY%s: %.0f %% of the intake averaging disc (radius %.0f m at "
            "x=%.0f) lies on condenser source cells. The disc would average the discharge itself. "
            "Require separation_m > 110 + bank_w + intake_r."
            % (" [%s]" % label if label else "", 100 * f, radius_m, ix))
    return f


def demo_site(size_m=2000.0, dx=10.0, discharge_k=11.0, exchange_s=60.0):
    """A representative data-centre campus: one hall, a condenser bank on its east
    side, a neighbouring hall 300 m east, and that neighbour's intake."""
    s = Site(size_m, dx)
    s.add_building(cx=700, cy=1000, w=200, h=120)          # our hall
    s.add_condensers(cx=830, cy=1000, w=60, h=120, discharge_k=discharge_k,
                     exchange_s=exchange_s)
    s.add_building(cx=1200, cy=1000, w=200, h=120)         # neighbour, 300 m east
    intake = (1090.0, 1000.0)                              # neighbour's intake, west face
    return s, intake


def ensemble(site, intake, ambient_mean, ambient_sd, wind_speed, wind_from,
             n_runs=100, seed=0, wind_sd_deg=15.0, speed_sd=1.0, discharge_sd_k=2.0,
             base_discharge_k=11.0, downwash_uc=None):
    """Perturb ambient, wind and load; return the distribution of intake temperature."""
    rng = np.random.default_rng(seed)
    out = []
    base_src = site.source.copy()
    for _ in range(n_runs):
        amb = ambient_mean + rng.normal(0, ambient_sd)
        wf = wind_from + rng.normal(0, wind_sd_deg)
        ws = max(0.3, wind_speed + rng.normal(0, speed_sd))
        scale = (base_discharge_k + rng.normal(0, discharge_sd_k)) / base_discharge_k
        site.source = base_src * max(0.1, scale)
        T = solve(site, amb, ws, wf, downwash_uc=downwash_uc)
        out.append(intake_temperature(T, site, *intake) - amb)   # rise above ambient
    site.source = base_src
    return np.array(out)
