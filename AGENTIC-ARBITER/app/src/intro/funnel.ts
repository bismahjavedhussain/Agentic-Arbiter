/**
 * THE CONVERGING MEASUREMENT LATTICE, the second half of the hero's motion.
 *
 * 🔴 THIS IS A REBUILD, AND THE STRUCTURE IS THE WHOLE POINT OF IT.
 * The first version scattered particles at random angles and radii. The user's verdict: "a random,
 * dense spray, it reads as confetti or static", against a reference that is "an ordered lattice:
 * regular rows and columns of dots laid on a curved surface, sparse and geometric, reading as a
 * measurement grid sweeping toward the planet." They are right, and RANDOMNESS was the mistake rather
 * than the density: a random field cannot have rows, so no amount of thinning would have produced one.
 *
 * So every dot now sits at an exact (u, v) address on a regular grid:
 *
 *      u = i / NU     ALONG the flow, 38 steps. Constant v traces a ROW toward the planet.
 *      v = j / NV     ACROSS the sheet, 20 steps. Constant u traces a COLUMN, an arc across it.
 *
 * and the whole grid drifts together, so the lattice moves as one rigid object and the rows stay
 * legible while it does. There is no noise term anywhere in the shape, which the brief asks for
 * explicitly: "no turbulence, no noise displacement." The only randomness left is a per-dot flicker
 * PHASE, which displaces nothing.
 *
 * DENSITY: 760 dots, down from 1,900. That is the brief's "cut density by roughly 60%" (a 60 % cut of
 * 1,900 is 760 exactly) and it is what makes individual dots, and whole rows, distinguishable.
 *
 * THE SHEET IS A FAN IN THE SCREEN PLANE WITH A GENTLE BOW, and that is the SECOND attempt at the
 * shape. The first was a cone slice: dots at radius r(u) around the funnel's axis, which points into
 * the planet. That is geometrically a converging lattice and it looked wrong, because a cone seen
 * end-on draws CONCENTRIC RINGS around the globe rather than a grid sweeping in from the left. The
 * rows were there and they curved over the top of the planet instead of arriving at it.
 *
 * So the fan opens in the plane of the screen, which is where the reference's does:
 *      L(u) = LENGTH * u^0.85            distance from the apex, so L(0) = 0 and every row meets there
 *      a    = (v - 0.5) * FAN            the fan angle, spreading the rows vertically
 *      x, y = apex + L * (cos a, sin a)  a polar grid: rows radiate, columns are arcs across them
 *      z    = BOW * L^2 / LENGTH         a quadratic bow toward the camera, so the sheet CURVES as it
 *                                        approaches and wraps over the limb rather than being flat
 * Rows are lines from the apex and columns are arcs crossing them, which is the structure the brief
 * describes: "regular rows and columns of dots laid on a curved surface".
 *
 * 🔴 EVERY POSITION IS COMPUTED IN THE VERTEX SHADER, AND THAT IS A PERFORMANCE DECISION.
 * The CPU alternative walks a Float32Array each frame and re-uploads it, on the same main thread as
 * React, GSAP and a MapLibre map. Here the grid addresses are written ONCE and the only per-frame data
 * crossing the boundary is one float uniform. The GPU does the curve.
 */
import * as THREE from 'three'

/** Steps along the flow. Constant `v` at successive `u` is one visible row. */
const NU = 38
/** Steps across the sheet. Constant `u` at successive `v` is one visible column. */
const NV = 20
/** 760. See the density note above: exactly a 60 % cut of the 1,900 the scatter version used. */
export const PARTICLE_COUNT = NU * NV

/**
 * The fan's total opening angle in radians. 0.80 is about +/- 23 degrees, measured off the reference:
 * its apex is at roughly (230, 310) of an 1100x584 frame and the dots reach about 470 px out with
 * +/- 200 px of vertical spread there, which is atan(200/470) = 23 degrees.
 */
const FAN = 0.8
/** How far the sheet bows toward the camera by the time it reaches the planet, in world units. This is
 *  the "curved surface": at 0 the fan is a flat plane, and past about 0.8 the near edge crosses in
 *  front of the globe's centre and the lattice reads as a dome rather than an approaching sheet. */
const BOW = 0.5
/** The radius the sheet is not allowed inside, with the earth at 1. Just clear of the surface, so the
 *  dots that arrive read as sitting ON the planet rather than buried in it or floating off it. */
const HUG = 1.045
/** One full traverse of the grid every 1/0.042 = about 24 s. Slow, per the brief. */
const DRIFT = 0.042
/** Uniform, per the brief, in CSS pixels before the device ratio. NOT perspective-scaled: the sheet is
 *  a lattice being read, and dots of varying size read as depth rather than as a grid. */
const DOT_PX = 3.0
/** Low, per the brief. Additive blending means this stacks where rows cross, which is wanted. */
const BASE_ALPHA = 0.72

export type Funnel = {
  points: THREE.Points
  /** Advance the drift. `t` is seconds; pass a constant to freeze it. */
  update: (t: number) => void
  /** Re-aim after a resize, in the globe group's own coordinates. */
  aim: (startX: number, endX: number) => void
  /** The x position, in normalised device coordinates, left of which dots fade to nothing. */
  guard: (ndcX: number) => void
  dispose: () => void
}

export function makeFunnel(pixelRatio: number): Funnel {
  const geo = new THREE.BufferGeometry()

  /* THE POSITION ATTRIBUTE IS REQUIRED AND UNUSED. three culls a BufferGeometry with no `position` and
     computes no bounding sphere for it, so the whole Points object would vanish on the first frustum
     test. It is filled with zeroes and the vertex shader ignores it; the bounding sphere is set by
     hand below, because one derived from points all at the origin would be a point and would cull the
     moment the origin left the frustum. */
  const position = new Float32Array(PARTICLE_COUNT * 3)
  /** The grid address. NOT random: `aGrid.x` is u and `aGrid.y` is v, both exact fractions. */
  const grid = new Float32Array(PARTICLE_COUNT * 2)
  /** Flicker phase only. The one place a hash is used, and it displaces nothing. */
  const phase = new Float32Array(PARTICLE_COUNT)

  /* Deterministic, never `Math.random()`: this project renders the same screen twice and requires the
     same answer, and a randomly seeded field would differ between the two renders for no reason
     anybody could diagnose. */
  const hash = (n: number) => {
    const s = Math.sin(n * 127.1 + 311.7) * 43758.5453
    return s - Math.floor(s)
  }

  let k = 0
  for (let i = 0; i < NU; i++) {
    for (let j = 0; j < NV; j++) {
      grid[k * 2] = i / NU
      grid[k * 2 + 1] = NV > 1 ? j / (NV - 1) : 0.5
      phase[k] = hash(k + 17)
      k++
    }
  }

  geo.setAttribute('position', new THREE.BufferAttribute(position, 3))
  geo.setAttribute('aGrid', new THREE.BufferAttribute(grid, 2))
  geo.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1))
  /* Generous, and centred where the sheet actually is. See the note on `position` above. */
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(-1.2, 0, 0), 4.5)

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uStart: { value: -2.2 },
      uEnd: { value: -0.85 },
      uFan: { value: FAN },
      uBow: { value: BOW },
      uHug: { value: HUG },
      uDrift: { value: DRIFT },
      uDot: { value: DOT_PX },
      uAlpha: { value: BASE_ALPHA },
      /* Anything left of this in normalised device coordinates fades to nothing. -2 disables it, since
         NDC never goes below -1. */
      uGuard: { value: -2 },
      uColor: { value: new THREE.Color(0x8fdcff) },
      uPixelRatio: { value: pixelRatio },
    },
    vertexShader: `
      uniform float uTime;
      uniform float uStart;
      uniform float uEnd;
      uniform float uFan;
      uniform float uBow;
      uniform float uHug;
      uniform float uDrift;
      uniform float uDot;
      uniform float uAlpha;
      uniform float uGuard;
      uniform float uPixelRatio;
      attribute vec2 aGrid;
      attribute float aPhase;
      varying float vAlpha;

      void main() {
        /* THE GRID DRIFTS AS ONE OBJECT. Every dot advances by the same amount, so rows stay rows.
           fract() wraps a dot that reaches the planet back to the point on the same frame, and the
           fades at both ends below are what make that seam invisible. */
        float u = fract(aGrid.x + uTime * uDrift);
        float v = aGrid.y;

        /* THE FAN, in polar coordinates about the apex. Eased so the columns open out of the point
           rather than crawling from it.
           L(0) = 0 exactly, which is what makes every row converge to ONE point. */
        float len = uEnd - uStart;
        float L = len * pow(u, 0.85);
        float a = (v - 0.5) * uFan;

        /* The bow is quadratic in L, so the sheet is flat where it is narrow and curves increasingly
           toward the camera as it widens and meets the planet. No noise term anywhere: the shape is a
           pure function of (u, v). */
        float z = uBow * L * L / max(0.001, len);
        vec3 p = vec3(uStart + L * cos(a), L * sin(a), z);

        /* 🔴 THE RADIAL CLAMP, AND IT IS WHAT MAKES THE LATTICE VISIBLE AT ALL.
           MEASURED: with the fan reaching to x = -0.1 and a bow of 0.5, its mouth landed at radius
           0.70 from the globe's centre, i.e. INSIDE a unit sphere, so the depth test correctly hid
           most of the grid and the screenshot showed one small surviving arc.
           Rather than shorten the fan (which made it too small to read as a grid) or crank the bow
           (which fixes the mouth and leaves the middle buried), any point that falls inside uHug is
           pushed straight out along its own direction until it sits on that radius. So the sheet flows
           in as a flat fan and then HUGS the planet where it arrives, which is the brief's "wrapping
           toward the globe on a curved path" expressed as three lines of arithmetic.
           It also preserves the lattice: the clamp is a radial scaling, so neighbouring dots stay
           neighbours and rows stay rows. */
        float rad = length(p);
        if (rad < uHug) p *= uHug / rad;

        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;

        /* UNIFORM, not perspective-divided. See the note on DOT_PX. */
        gl_PointSize = uDot * uPixelRatio;

        /* Fade in out of the point and out again as the sheet meets the planet, so nothing pops at the
           wrap and the rows do not terminate on a hard edge. */
        float fade = smoothstep(0.0, 0.10, u) * (1.0 - smoothstep(0.80, 1.0, u));

        /* 🔴 THE TYPE GUARD. The brief: "Keep the left 38% of the viewport completely free of
           particles." Tested in normalised device coordinates, the only space this shader can check
           without being told anything about the viewport; HeatGlobe.tsx converts the 38 % into this
           number. The lattice is also PLACED to the right of it, so this is the guarantee rather than
           the mechanism: a resize or a drag cannot walk the mesh into the headline. */
        float ndcX = gl_Position.x / gl_Position.w;
        float guard = smoothstep(uGuard, uGuard + 0.10, ndcX);

        /* The brief's "gentle per-dot opacity flicker". Never below 0.86, so it reads as a live
           instrument rather than as dropped frames, and it moves nothing. */
        float flick = 0.93 + 0.07 * sin(uTime * (0.9 + aPhase * 1.6) + aPhase * 40.0);

        vAlpha = uAlpha * fade * guard * flick;
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      varying float vAlpha;
      void main() {
        /* A round dot with a soft edge, and the cheapest possible circle: gl_PointCoord is the sprite's
           own unit square, so there is no texture to load, decode or dispose. */
        float d = length(gl_PointCoord - vec2(0.5));
        float m = 1.0 - smoothstep(0.18, 0.5, d);
        if (m * vAlpha <= 0.002) discard;
        gl_FragColor = vec4(uColor, m * vAlpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    /* Tested against the planet so the sheet is occluded where it passes behind the limb, but not
       WRITTEN, so dots do not occlude each other and the additive build-up where rows cross survives. */
    depthTest: true,
    depthWrite: false,
  })

  const points = new THREE.Points(geo, mat)
  /* Drawn after the opaque planet regardless of position, which additive transparency needs in order to
     composite over what is behind it. */
  points.renderOrder = 2

  return {
    points,
    update: (t: number) => {
      mat.uniforms.uTime.value = t
    },
    aim: (startX: number, endX: number) => {
      mat.uniforms.uStart.value = startX
      mat.uniforms.uEnd.value = endX
    },
    guard: (ndcX: number) => {
      mat.uniforms.uGuard.value = ndcX
    },
    dispose: () => {
      geo.dispose()
      mat.dispose()
    },
  }
}
