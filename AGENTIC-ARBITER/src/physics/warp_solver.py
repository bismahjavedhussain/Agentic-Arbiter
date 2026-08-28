# -*- coding: utf-8 -*-
"""NVIDIA Warp port of the advection-diffusion timestep, batched over an ensemble.

WHY THE GPU IS LOAD-BEARING HERE, NOT DECORATIVE
    A single solve is not the workload. The BOUND is the workload: to state "90 % of the time the
    intake stays under X" the physics has to run many times over a spread of ambient conditions,
    wind directions and load assumptions, and the distribution that comes out is the product. That
    is an embarrassingly parallel ensemble, which is exactly what a GPU is for.

    The batch dimension is the ensemble member. Every member advances one timestep in a single
    kernel launch, and nothing returns to host memory until the run finishes.

The kernel is a line-for-line port of solver.solve()'s inner step, including:
    - upwind differencing where there is flow, central differencing below EPS (calm)
    - inflow boundaries held at ambient, outflow zero-gradient (edge clamp)
    - obstacle cells pinned to ambient
    - the plume-rise downwash closure, applied host-side by scaling each member's source
"""
import numpy as np

try:
    import warp as wp
    HAVE_WARP = True
except Exception:
    HAVE_WARP = False

EPS = 1.0e-2


if HAVE_WARP:
    wp.init()

    @wp.kernel
    def step_kernel(T: wp.array3d(dtype=wp.float32),
                    Tnew: wp.array3d(dtype=wp.float32),
                    src: wp.array3d(dtype=wp.float32),
                    obstacle: wp.array2d(dtype=wp.int32),
                    u: wp.array(dtype=wp.float32),
                    v: wp.array(dtype=wp.float32),
                    dt: wp.array(dtype=wp.float32),
                    ambient: wp.array(dtype=wp.float32),
                    dx: wp.float32, diffusivity: wp.float32, n: wp.int32):
        b, i, j = wp.tid()

        ub = u[b]
        vb = v[b]
        amb = ambient[b]
        C = T[b, i, j]

        # ---- neighbours, with the same boundary rules as the NumPy version -----
        # west (j-1): inflow held at ambient when the wind comes from the west,
        # otherwise zero-gradient, which for the first cell means the cell itself
        W = C
        if j > 0:
            W = T[b, i, j - 1]
        else:
            if ub > EPS:
                W = amb

        E = C
        if j < n - 1:
            E = T[b, i, j + 1]
        else:
            if ub < -EPS:
                E = amb

        S = C
        if i > 0:
            S = T[b, i - 1, j]
        else:
            if vb > EPS:
                S = amb

        N = C
        if i < n - 1:
            N = T[b, i + 1, j]
        else:
            if vb < -EPS:
                N = amb

        # ---- upwind where there is flow, central where there is not -----------
        dTdx = (E - W) / (wp.float32(2.0) * dx)
        if ub > EPS:
            dTdx = (C - W) / dx
        if ub < -EPS:
            dTdx = (E - C) / dx

        dTdy = (N - S) / (wp.float32(2.0) * dx)
        if vb > EPS:
            dTdy = (C - S) / dx
        if vb < -EPS:
            dTdy = (N - C) / dx

        adv = -(ub * dTdx + vb * dTdy)
        lap = (N + S + E + W - wp.float32(4.0) * C) / (dx * dx)
        val = C + dt[b] * (adv + diffusivity * lap + src[b, i, j])

        # OBSTACLE PINNING REMOVED 2026-08-12. This used to do `if obstacle[i,j]==1: val = amb`,
        # matching the CPU path. Both were wrong: pinning a cell to ambient is a fixed-temperature
        # boundary, which ABSORBS heat without limit. N-29 measured a 120 x 200 m building removing
        # 99.7 % of a crossing plume, against 100.0 % conserved in the open domain. Real air flows
        # AROUND a building; it is not annihilated by one.
        #
        # Obstacles are now TRANSPARENT to the temperature field. That is also not exactly right --
        # the flow should be deflected -- but it is wrong in a stated, bounded way rather than a
        # catastrophic one, and it conserves heat. The obstacle mask is still used for two things:
        # excluding building interiors from the intake average, and the line-of-sight check in
        # solver.path_blocked(). See solver.solve() for the full reasoning and the ASHRAE basis.
        Tnew[b, i, j] = val


def _wind_components(speed, from_deg):
    th = np.radians(np.asarray(from_deg, dtype=np.float64) + 180.0)
    return np.asarray(speed) * np.sin(th), np.asarray(speed) * np.cos(th)


def solve_batch(site, ambients, speeds, from_degs, source_scales,
                diffusivity=8.0, steps=800, device="cuda", downwash=None):
    """Advance an entire ensemble on the GPU. Returns (n_members, n, n) float32.

    ambients / speeds / from_degs / source_scales are per-member sequences.
    `downwash` is the per-member fraction of discharge retained in the layer (the N-11 closure);
    pass None for 1.0, matching solver.solve(downwash_uc=None).
    """
    if not HAVE_WARP:
        raise RuntimeError("warp-lang is not installed")

    B, n, dx = len(ambients), site.n, float(site.dx)
    u, v = _wind_components(speeds, from_degs)

    # same COMBINED stability limit as the NumPy solver: advection and diffusion share dt
    dt = 0.4 / ((np.abs(u) + np.abs(v)) / dx + 4.0 * diffusivity / (dx * dx) + 1e-12)

    dw = np.ones(B) if downwash is None else np.asarray(downwash, dtype=np.float64)
    src = (site.source[None, :, :].astype(np.float32)
           * (np.asarray(source_scales, dtype=np.float64) * dw)[:, None, None].astype(np.float32))

    T0 = np.repeat(np.asarray(ambients, dtype=np.float32)[:, None, None], n, axis=1).repeat(n, axis=2)

    d_T = wp.array(T0, dtype=wp.float32, device=device)
    d_Tn = wp.array(np.empty_like(T0), dtype=wp.float32, device=device)
    d_src = wp.array(src, dtype=wp.float32, device=device)
    d_obs = wp.array(site.obstacle.astype(np.int32), dtype=wp.int32, device=device)
    d_u = wp.array(u.astype(np.float32), dtype=wp.float32, device=device)
    d_v = wp.array(v.astype(np.float32), dtype=wp.float32, device=device)
    d_dt = wp.array(dt.astype(np.float32), dtype=wp.float32, device=device)
    d_amb = wp.array(np.asarray(ambients, dtype=np.float32), dtype=wp.float32, device=device)

    for _ in range(steps):
        wp.launch(step_kernel, dim=(B, n, n),
                  inputs=[d_T, d_Tn, d_src, d_obs, d_u, d_v, d_dt, d_amb,
                          wp.float32(dx), wp.float32(diffusivity), wp.int32(n)],
                  device=device)
        d_T, d_Tn = d_Tn, d_T          # swap; no host transfer inside the loop

    wp.synchronize()
    return d_T.numpy()
