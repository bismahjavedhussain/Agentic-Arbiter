/**
 * THE HERO EARTH. A photoreal, lit, cloud-wrapped sphere with a cyan atmospheric rim and a converging
 * funnel of particles sweeping in from the left, deliberately too big for the frame and cropped by the
 * right edge of the viewport.
 *
 * 🔴 THIS REPLACES A cobe DOT GLOBE, AND THE REPLACEMENT IS TOTAL RATHER THAN A RETUNE.
 * The user's brief is explicit about why: "These are different technologies -- do not try to tune
 * what's there." That is correct, and it is worth writing down which of cobe's properties made it
 * the wrong tool rather than merely a different one:
 *   - cobe rasterises a DOT MATRIX sampled from a landmass mask (`mapSamples: 15000`). There is no
 *     texture input at all, so a satellite image cannot be shown on it at any setting.
 *   - it has no light, so it has no terminator, and a sphere with no day/night edge reads as a disc.
 *   - its glow is a flat halo, not a fresnel: the falloff does not depend on the view angle, so it
 *     cannot be strongest at the limb.
 * Three.js was chosen for the same three reasons in reverse, and its cost is stated rather than
 * hidden: it is the largest single dependency in this app. The previous note in this file argued
 * cobe on bundle size, and that argument was RIGHT ON ITS OWN TERMS and lost to a design requirement
 * it could not meet. Both halves are recorded so the trade is not re-litigated from half of it.
 * See `04-STANDING-RULES.md` C5.
 *
 * 🔴 THE TEXTURES ARE SELF-HOSTED AND THE PATH IS `ART`, EXACTLY AS THE AUDIO IS.
 * `demo/textures/`, fetched through `ART` ('../'), so they resolve in vite dev, under
 * `testing/serve_app.py` at /app/, and in production at `demo/app/` without a path change. Four
 * files, 1.19 MB, CC BY 4.0, prepared by `tools/make_earth_textures.py`, attribution in
 * `demo/textures/CREDITS.txt`. Nothing is hotlinked: this page must work offline.
 *
 * 🔴 THE NORMAL MAP IS AMPLIFIED, AND THE NUMBER COMES FROM A MEASUREMENT.
 * The source map's stddev is 1.36 of 255 with the blue channel a constant 255, because Earth's real
 * relief is 9 km on a 6,371 km radius and a correctly scaled normal map is therefore nearly flat. At
 * `normalScale` 1 it is invisible. `tools/make_earth_textures.py` carries the measurement and the
 * reason that one file ships as lossless PNG.
 *
 * 🔴 THE COMPOSITION IS COMPUTED HERE, NOT IN CSS, AND THAT IS A CORRECTION.
 * The first version split it: CSS sized and offset a square canvas, and this file set a camera
 * distance that assumed the sphere filled a particular fraction of it. Two files each holding half a
 * guess about the other. It also could not work for the funnel, which has to originate near the LEFT
 * EDGE OF THE VIEWPORT while the globe sits to the right, so the canvas has to cover the viewport
 * rather than being a box positioned inside it.
 * Now CSS does one thing: a square that covers the viewport (`max(100vw, 100vh)`, left-aligned,
 * vertically centred). Everything about where the planet actually lands is measured and solved below,
 * from three numbers a human can reason about: how big the sphere is, and where its left and top
 * limbs fall.
 * A useful property falls out of it. The canvas covers the viewport EXACTLY at the left edge, so the
 * camera frustum's boundary and the viewport's boundary coincide, which means any clipping is the
 * intended crop rather than an accident. The first version clipped the atmosphere at the canvas edge
 * and left a straight vertical line down the screenshot where a curved rim glow belongs.
 */
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { ART } from '../lib/artefacts'
import { makeFunnel, type Funnel } from './funnel'
import { registerDolly } from './globeDolly'

/** Prepared by tools/make_earth_textures.py. Fetched through ART for the reason stated above. */
const TEX = {
  day: ART + 'textures/earth_daymap.jpg',
  clouds: ART + 'textures/earth_clouds.jpg',
  normal: ART + 'textures/earth_normal.png',
  specular: ART + 'textures/earth_specular.jpg',
}

/** One revolution in 78 s, inside the brief's 60 to 90 s window. Radians per second. */
const SPIN = (Math.PI * 2) / 78
/** The cloud deck turns slightly faster, so weather drifts over the ground rather than being
 *  painted on it. 1.22x, which is enough to notice over 20 s and not enough to look like wind. */
const CLOUD_SPIN = SPIN * 1.22

const FOV = 26
const HALF_TAN = Math.tan(((FOV / 2) * Math.PI) / 180)

/**
 * 🔴 THE FRAMING IS ALL RATIOS OF THE MEASURED CONTAINER, AND THE CAMERA DISTANCE IS DERIVED FROM
 * THEM. That is a change of approach, and it is the user's: the previous round asked for a single
 * `CAMERA_Z` constant, and this one asks to "derive camera distance from the container's measured
 * height so the ratio holds at any viewport size. Recompute on resize."
 *
 * The reason they gave is worth keeping, because it is the flaw in the constant: an absolute pixel
 * diameter "assumed a 1080px viewport. The real container is ~910px tall after browser chrome, so that
 * value is too large." A fixed camera distance has exactly that problem one level down, since the
 * apparent size then follows the CANVAS rather than the container.
 *
 * So there are three ratios and the camera falls out of them:
 *
 *      pxPerWorld = (diameterOfH * H) / 2        the sphere's radius is 1 world unit
 *      halfH      = (canvas side / 2) / pxPerWorld
 *      cameraZ    = halfH / tan(FOV/2)
 *
 * `applyLayout()` runs this on mount and from the ResizeObserver, so the ratio holds at every size.
 * ⚠ IT IS STILL THE CAMERA THAT MOVES. `mesh.scale` is never touched, for the reason the brief gives
 * and repeats: the atmosphere is a separate shell at a fixed radius, so scaling the earth would shrink
 * the planet and leave the glow floating at its old size.
 */
/**
 * The atmosphere shell's radius, with the earth at 1. 🔴 REDUCED FROM 1.15 during the halo pass, and it
 * is half of what removed the wide dark band: the radius caps how far OUT the glow can reach at all, so
 * a sharper falloff alone would still leave a faint outer skirt. At a 0.90 H diameter this is a band of
 * about 9 % of the planet's radius.
 * ⚠ It must stay above 1.0 or the shell intersects the earth and the rim disappears into the surface.
 */
const ATMO_RADIUS = 1.09

/**
 * HOW FAR THE LAUNCH SEQUENCE'S PUSH-IN TRAVELS: a 16 % reduction in camera distance at k = 1.
 *
 * 🔴 A FRACTION OF THE SOLVED DISTANCE, NOT AN ABSOLUTE ONE, and that is what makes it survive a
 * resize. `applyLayout()` re-solves `cameraZ` from the container's measured height, so a timeline that
 * had written an absolute z would be overwritten on the next ResizeObserver tick and the push-in would
 * snap back mid-sequence. The dolly is stored and re-applied instead.
 * 16 % is enough that the planet is visibly growing over five seconds and not enough to break the
 * framing the user measured and signed off: at k = 1 the diameter goes from 0.90 to about 1.07 of H,
 * which is why the sequence ENDS there rather than living at it.
 */
const DOLLY_RANGE = 0.16

const FRAME = {
  /** Sphere diameter as a fraction of the container HEIGHT. Down from an effective 1.14 of H, which
   *  is the inversion the user identified: at that size the top was clipped and the bottom sat just
   *  inside the frame, which is the reference upside down. */
  diameterOfH: 0.9,
  /** Sphere centre. 0.66 of the height puts it BELOW the vertical midpoint, which is what produces
   *  clearance above and a crop below rather than the other way round. */
  centreOfW: 0.72,
  centreOfH: 0.66,
}

/**
 * THE THREE CONSEQUENCES THE BRIEF USES AS ITS CHECK, and they are arithmetic on the ratios above
 * rather than separate settings, which is why they cannot be tuned independently:
 *
 *      top of sphere    = 0.66 H - 0.45 H = 0.21 H     so about 20 % of H is clear above it
 *      bottom of sphere = 0.66 H + 0.45 H = 1.11 H     so it is cropped by 0.11 H
 *      left limb        = 0.72 W - 0.45 H              visible on any window wider than about 0.63 H
 *
 * ⚠ AND THE FOURTH ONE, "cropped by the viewport right edge", DEPENDS ON THE ASPECT RATIO. The right
 * edge is at 0.72 W + 0.45 H, so it is cropped only when 0.45 H > 0.28 W, i.e. when W < 1.61 H. At a
 * 1920 x 1020 window (container about 1902 x 924) that is W < 1486, so the sphere is NOT cropped on
 * the right there: it stops about 120 px short. It IS cropped on any window narrower than that. This
 * is stated rather than quietly fixed because the two numbers it follows from are both the user's.
 */

/** Narrow: driven off the WIDTH instead, because 0.9 of a phone's height is wider than the phone. */
const NARROW_FRAME = {
  diameterOfW: 1.0,
  centreOfW: 0.5,
  centreOfH: 0.42,
}

/**
 * WHERE THE LATTICE LIVES, as fractions of the viewport width plus one world-space end point.
 *
 * 🔴 `guardOfWidth` IS A HARD REQUIREMENT, NOT A STYLE CHOICE. The brief: "Keep the left 38% of the
 * viewport completely free of particles ... The reference keeps the mesh entirely clear of the text
 * block." So the sheet is PLACED to the right of it and the shader also FADES anything that ends up
 * left of it, because a placement can be walked out of position by a resize or a drag and a guarantee
 * cannot.
 * `startOfWidth` is where the rows converge. It sits just right of the guard rather than off-frame:
 * the convergence point is the one part of the lattice's shape a reader can actually read, and the
 * supplied reference has it plainly on screen.
 */
const FUNNEL = {
  guardOfWidth: 0.38,
  startOfWidth: 0.41,
  /** In world units, relative to the sphere's centre, and with the fan it is the sheet's far END
   *  rather than a stopping line: the lattice runs from `startOfWidth` to here.
   *  -0.10 is just left of the sphere's centre, so the sheet arrives on the limb and carries a little
   *  way across the face, which is the reference's proportion: its dots reach roughly 39 % of the way
   *  across the disc. Stopping at the limb left the fan too short to read as a grid at all. */
  endWorld: -0.1,
}


/**
 * WHERE IT STARTS FACING: the Americas, because every facility in this project's registry is in the
 * United States and a hero globe showing somewhere else is scenery about somewhere else.
 *
 * 🔴 MEASURED IN TWO RENDERS, NOT DERIVED, AND THE DERIVATION IS LEFT HERE BECAUSE IT WAS WRONG.
 * From three's own SphereGeometry the equator maps to x = -cos(2*PI*u), z = sin(2*PI*u), the camera
 * sits on +Z, and an equirectangular texture puts longitude -180 at u = 0. Solving for the point
 * facing the camera gives L = -90 - a * 180/PI, i.e. rotation.y = 0 should face longitude -90 and put
 * North America dead centre. IT DOES NOT. So rather than keep guessing which of the geometry, the
 * texture's own orientation and `flipY` is responsible, the constant was MEASURED: two renders one
 * radian apart, the sub-camera point identified in each image, and the line through them.
 *
 *      a = 0.53  ->  centre in the Gulf of Guinea, about   +5 E
 *      a = 1.53  ->  centre in the mid-Atlantic, about    -52 E
 *
 * Two candidate lines fitted the first point; the second render chose between them, because they
 * predicted +62 E (the Arabian Sea) and -52 E (the mid-Atlantic) and only one of those is an ocean
 * between two continents you can identify at a glance. So:
 *
 *      centre longitude L = 35.4 - a * 180/PI       i.e. turning it UP moves the view WEST
 *
 * Solving for -85 E, which puts the continental United States just left of the sphere's centre and
 * therefore near the middle of the part the viewport actually shows: a = (35.4 + 85) * PI/180 = 2.101
 *
 * ⚠ This is the same trap the cobe version hit and recorded in this file: "left as plain numbers with
 * the measurements beside them, rather than a formula that looked principled and was wrong twice."
 * It was wrong twice again. The measurements are the answer; the derivation is kept only so nobody
 * re-derives it and trusts the result.
 */
const START_Y = 2.101
/** A small axial tilt. Earth's is 23.4 degrees; at this framing the full tilt puts the north pole in
 *  shot and flattens the limb, so this is half of it. Stated as a fraction of the real value rather
 *  than as a bare number, so it cannot read as arbitrary. */
const TILT = (23.4 / 2) * (Math.PI / 180)
/** The funnel's axis is tilted so it arrives at the planet's upper left rather than dead level, which
 *  is the reference's line. Negative rotates the far (convergence) end upward. */
const FUNNEL_TILT = -0.2

export function HeatGlobe({ reduced, narrow }: { reduced: boolean; narrow: boolean }) {
  const canvas = useRef<HTMLCanvasElement | null>(null)
  const wrap = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const el = canvas.current
    const host = wrap.current
    if (!el || !host) return

    /* The canvas is square, which is what keeps a sphere a sphere: the camera's aspect is fixed at 1,
       and `verify_intro.py` asserts the drawn box is square for exactly that reason. */
    const side = () => Math.max(1, Math.round(Math.min(el.clientWidth, el.clientHeight)))

    /**
     * 🔴 WEBGL MAY NOT EXIST, AND WITHOUT THIS THE WHOLE PRODUCT WENT BLANK.
     *
     * `new THREE.WebGLRenderer()` does not return null when it cannot get a context: it THROWS
     * ("THREE.WebGLRenderer: Error creating WebGL context"). Thrown from inside a `useEffect`, with no
     * error boundary above it, React unmounts the entire tree. MEASURED with `--disable-webgl`:
     * `#root` went from 1 child to 0 and the page was empty. Not a degraded globe, not a missing
     * decoration: nothing at all, on a machine whose only fault is that 3D is turned off.
     *
     * ⚠ AND EVERY CHECK IN THIS REPOSITORY MISSED IT, because every one of them launches Chrome with
     * `--enable-unsafe-swiftshader --use-gl=angle` so that MapLibre can render. A harness that always
     * supplies the thing under test cannot see its absence. That is 05-TRAPS 5b.7 in another costume.
     *
     * So the renderer is attempted, and a failure means NO GLOBE and a working page. The splash keeps
     * its floor, its type and its call to action; only the scenery is gone. There is deliberately no
     * message: a reader who has WebGL off does not need to be told what they are not seeing.
     * `IntroBoundary` in App.tsx is the belt to this brace.
     */
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: el,
        antialias: true,
      /* Transparent, so the splash's own near-black navy shows through and the additive rim glow and
         particles composite over it. A clear colour here would be a second owner of the hero's
         background. */
        alpha: true,
        powerPreference: 'high-performance',
      })
    } catch {
      /* No context, and nothing else in this effect can run without one. Returning here leaves the
         canvas empty and every listener unbound, which is exactly the wanted end state. */
      return
    }

    /* 🔴 THE DRAWING BUFFER IS CAPPED BY AREA, NOT BY devicePixelRatio, and the cap is the whole
       performance story here.
       The brief's bar is 60 fps on a mid-range laptop, which is 16.7 ms a frame. The geometry is
       irrelevant at ~24,000 triangles; what costs is FRAGMENTS, because every one runs a
       normal-mapped Phong, and over the limb an additional fresnel, and over the funnel an additive
       blend. This canvas is deliberately larger than the viewport, and its size is set by the
       reader's window rather than by anything here, so a fixed ratio is not a bound on anything.
       Capping the AREA at 2.4 million pixels makes the per-frame cost the same however big the
       window is, which is the property a fixed ratio does not have. The brief's own order (segments
       before texture quality) is untouched: this is cheaper than either and is reached first. */
    const MAX_BUFFER_PX = 2.4e6
    const ratioFor = (s: number) =>
      Math.max(0.75, Math.min(1.75, window.devicePixelRatio || 1, Math.sqrt(MAX_BUFFER_PX) / s))
    renderer.setPixelRatio(ratioFor(side()))
    renderer.setSize(side(), side(), false)
    renderer.setClearAlpha(0)
    renderer.outputColorSpace = THREE.SRGBColorSpace

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 100)

    /* ---- TEXTURES. One loader, so a single dispose list covers all four.
       colorSpace matters and is easy to get silently wrong: the day map is authored in sRGB and must
       be declared so, while the normal and specular maps carry DATA rather than colour and must stay
       linear. Marking a normal map as sRGB bends every normal it encodes.
       ITS OWN LoadingManager, not `THREE.DefaultLoadingManager`: the default is module-global and
       shared with anything else in the process that loads through three, so setting `onLoad` on it
       would be this component reaching outside itself. */
    const manager = new THREE.LoadingManager()
    const loader = new THREE.TextureLoader(manager)
    const textures: THREE.Texture[] = []
    const load = (url: string, srgb: boolean) => {
      const t = loader.load(url)
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace
      t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
      textures.push(t)
      return t
    }

    /* 64 segments. The brief names this figure and also names it as the first thing to cut for frame
       rate, ahead of texture quality. At 64x64 the silhouette is smooth at this size; the whole scene
       is about 24,000 triangles, which is not what costs frames here. */
    const SEG = 64

    /* 🔴 ONE GROUP FOR THE PLANET, and the reason is that three separate meshes cannot share a
       composition. The earth, its clouds and its atmosphere are concentric; positioning them
       individually means three chances to put one of them a fraction out and get a crescent of
       atmosphere on one side. The group is positioned, and the axial tilt is on the group, so the
       clouds and the rim stay registered with the ground. */
    const globe = new THREE.Group()
    globe.rotation.z = TILT
    scene.add(globe)

    const earthGeo = new THREE.SphereGeometry(1, SEG, SEG)
    const earthMat = new THREE.MeshPhongMaterial({
      map: load(TEX.day, true),
      normalMap: load(TEX.normal, false),
      /* AMPLIFIED, for the measured reason in the header: the source signal is 1.36/255 wide. 2.8 is
         where coastal relief and the Andes read without the flat ocean starting to shimmer. */
      normalScale: new THREE.Vector2(2.8, 2.8),
      /* THE SPECULAR MAP IS WHAT MAKES IT LOOK WET. White over ocean, black over land, so the
         highlight lands only on water. Without it the whole globe takes the same sheen and the
         continents look laminated. */
      specularMap: load(TEX.specular, false),
      specular: new THREE.Color(0x2a4a6a),
      shininess: 12,
    })
    const earth = new THREE.Mesh(earthGeo, earthMat)
    earth.rotation.y = START_Y
    globe.add(earth)

    /* ---- THE CLOUD DECK. A second sphere 1 % larger, its texture read as an ALPHA map rather than a
       colour map: the file is greyscale cloud cover, so used as `map` it would paint grey clouds, and
       used as `alphaMap` it punches white through where cloud is. Dropped entirely on a narrow
       screen, per the brief. */
    let clouds: THREE.Mesh | null = null
    let cloudGeo: THREE.SphereGeometry | null = null
    let cloudMat: THREE.MeshPhongMaterial | null = null
    if (!narrow) {
      cloudGeo = new THREE.SphereGeometry(1.01, SEG, SEG)
      cloudMat = new THREE.MeshPhongMaterial({
        alphaMap: load(TEX.clouds, false),
        transparent: true,
        opacity: 0.45,
        /* Not written to the depth buffer: it is a translucent shell over an opaque one, and writing
           depth here makes the cloud sphere occlude the atmosphere behind it in a way that shows as a
           hard ring at the limb. */
        depthWrite: false,
        color: 0xffffff,
      })
      clouds = new THREE.Mesh(cloudGeo, cloudMat)
      clouds.rotation.y = START_Y
      globe.add(clouds)
    }

    /* ---- THE ATMOSPHERE. This is the effect the whole dark background exists for.
       A third sphere at 1.15 rendered from the INSIDE (`BackSide`), with a fresnel term: the glow's
       strength depends on the angle between the surface normal and the view direction, so it is
       brightest exactly where the sphere turns away from the camera, which is the limb. That angular
       dependence is what a flat halo cannot reproduce and it is why this is a shader rather than a
       sprite.
       Additive, and therefore INVISIBLE ON WHITE: adding light to a surface already at maximum
       changes nothing. That is the arithmetic behind the brief's non-negotiable dark background, and
       it is also the explanation for the flat look the user reported on the old version. */
    const atmoGeo = new THREE.SphereGeometry(ATMO_RADIUS, SEG, SEG)
    const atmoMat = new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: new THREE.Color(0x4db8ff) },
        uCore: { value: new THREE.Color(0x7fd4ff) },
        uIntensity: { value: 1.9 },
        /* 🔴 THE FALLOFF EXPONENT, AND RAISING IT IS WHAT REMOVES THE DARK NAVY BAND.
           The user: "The problem is the wide dark navy band sitting inside it. Reference has
           essentially only the thin bright halo." They diagnosed it correctly. This shell is
           ADDITIVE, so it cannot darken anything; what looked like a dark band was this shader's own
           LOW-RIM TAIL adding a dim navy wash across a wide annulus. Additive blending multiplies by
           the source alpha, which is also `rim`, so the contribution goes as rim^2 and at exponent
           3.2 a point one third of the way in still contributed about 0.5 % of full brightness over
           a very large area, which over near-black reads as a band.
           At 6.4 that same point contributes 4e-6, i.e. nothing. MEASURED as a width: the visible
           glow is about half what it was, which is the target the brief set.
           The intensity is raised from 1.15 to 1.9 at the same time, because a sharper falloff makes
           the remaining arc darker as well as thinner, and the thin bright arc is the part that was
           already right. */
        uPower: { value: 6.4 },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          vView = -mv.xyz;
          gl_Position = projectionMatrix * mv;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform vec3 uCore;
        uniform float uIntensity;
        uniform float uPower;
        varying vec3 vNormal;
        varying vec3 vView;
        void main() {
          /* abs(), because BackSide flips the normal: the sign of the dot product depends on which
             face is being rasterised and the rim term must not. */
          float facing = abs(dot(normalize(vNormal), normalize(vView)));
          float rim = pow(clamp(1.0 - facing, 0.0, 1.0), uPower);
          /* The hottest part of the rim shifts toward the paler blue, which is what an atmosphere
             does: the thinnest air scatters the shortest wavelengths hardest. */
          vec3 c = mix(uColor, uCore, clamp(rim * 1.35, 0.0, 1.0));
          gl_FragColor = vec4(c * uIntensity * rim, rim);
        }
      `,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false,
    })
    const atmosphere = new THREE.Mesh(atmoGeo, atmoMat)
    globe.add(atmosphere)

    /* ---- THE PARTICLE FUNNEL. Dropped entirely on a narrow screen, per the brief.
       In its OWN group rather than inside `globe`, because it must not inherit the planet's axial
       tilt or its rotation: it has its own tilt, and it is a stream arriving at the planet rather
       than something attached to it. */
    let funnel: Funnel | null = null
    const funnelGroup = new THREE.Group()
    if (!narrow) {
      funnelGroup.rotation.z = FUNNEL_TILT
      funnel = makeFunnel(renderer.getPixelRatio())
      funnelGroup.add(funnel.points)
      scene.add(funnelGroup)
    }

    /* ---- LIGHT. One directional light, placed to the left and slightly in front, so the terminator
       falls across the right third: that is the side the viewport crops, so the day/night edge is
       inside the frame rather than hidden behind it. The z component is what decides where it lands;
       at 2.1 the light was almost behind the camera and the whole visible face was lit flat with no
       day/night edge at all in the first capture.
       AND A LOW BLUE AMBIENT, not a grey one. The dark side of a planet is not neutral grey; it is
       lit by the same scattered blue the rim glow is made of, and a grey ambient here is the single
       change that makes a globe look like a plastic ball. */
    /* 🔴 THE LIGHT MOVED TWICE, AND THE SECOND MOVE WAS THE FUNNEL'S DOING RATHER THAN THE PLANET'S.
       First it sat at z = 2.1, almost behind the camera, and the whole visible face was lit flat with
       no day/night edge at all. Pulling z back to 1.15 with the light out to the LEFT fixed that and
       produced a good terminator on the right.
       Then the particle funnel arrived, and the funnel comes in from the LEFT. Lit from the left, the
       planet's left limb is its brightest region, so 1,900 small cyan dots over it read as scattered
       noise on a bright ocean rather than as a stream arriving out of the dark. The supplied reference
       does not have that problem because its globe is lit from the RIGHT: its left limb is in shadow,
       which is what the dots glow against.
       So the light is now slightly to the right of head-on and above. The terminator falls near both
       limbs, the middle (where the continents are) stays bright, and the left limb is dark enough for
       the funnel to read against. The subtle day/night edge the brief asks for is still there; it is
       on the side the funnel needs it. */
    const sun = new THREE.DirectionalLight(0xfff4e6, 2.8)
    /* ⚠ MOVED FURTHER RIGHT AGAIN with the lattice rebuild, and only because the lattice needs it.
       At 0.55 the light was near head-on, which left the planet's left limb bright enough that a
       sparse grid of pale cyan dots over it competed with the ocean instead of reading against it.
       The supplied reference lights its globe from the right for exactly this reason: its left limb is
       in shadow and the mesh glows against it. 1.15 darkens the left third without pushing the
       terminator far enough to dim North America, which is the half of the planet this product is
       about. */
    sun.position.set(1.15, 0.7, 1.85)
    scene.add(sun)
    /* Raised from 0.6 with the atmosphere pass. Part of what read as a "dark navy band" is the PLANET's
   own unlit limb, which no change to the shell can fix, and a little more scattered blue there
   separates the surface from the halo instead of the two merging into one dark ring. */
    const ambient = new THREE.AmbientLight(0x16324c, 0.78)
    scene.add(ambient)

    /** The distance `applyLayout()` last solved, before the push-in. */
    let solvedZ = 0
    /** The launch sequence's push-in, 0 to 1. */
    let dolly = 0
    /** The ONLY writer of `camera.position.z`. */
    const applyCamera = () => {
      camera.position.z = solvedZ * (1 - DOLLY_RANGE * dolly)
    }

    /* 🔴 THE PUSH-IN ARRIVES THROUGH A REGISTRY, not a prop or a ref. `intro/globeDolly.ts` explains
       why; the short version is that the timeline is built in a sibling of this component's parent and
       a ref would still be null on its first frame.
       In the static modes the scene is rendered once and stops, so a dolly update has to ask for a
       frame or the camera would move with nothing drawing it. */
    /** Last value published to the DOM, so the attribute is written on change rather than per frame. */
    let publishedDolly = -1
    const unregisterDolly = registerDolly((k) => {
      dolly = k
      applyCamera()
      /* 🔴 PUBLISHED SO THE PUSH-IN CAN BE MEASURED AT ALL. `data-aa-sphere` carries what
         `applyLayout()` SOLVED, which is the resting framing and does not move while the camera
         travels: a probe comparing it at two moments during the sequence reported no change for a
         camera that was moving the whole time.
         THROTTLED TO 0.02, because this is a DOM write inside a 60 Hz tween. That is about fifty
         writes across the whole sequence instead of four hundred, and 0.02 of a 16 % travel is a
         quarter of a pixel at this size, so nothing measurable is lost. */
      if (Math.abs(k - publishedDolly) >= 0.02 || k === 0 || k === 1) {
        publishedDolly = k
        el.dataset.aaDolly = String(Math.round(k * 1000) / 1000)
      }
      if (reduced || narrow) renderer.render(scene, camera)
    })

    /**
     * 🔴 THE ONE PLACE THE COMPOSITION IS SOLVED. Called on mount and on every resize.
     *
     * The camera distance is DERIVED here from the container's measured height, which is what the
     * latest brief asks for and which the previous fixed constant could not do: a fixed distance ties
     * the apparent size to the CANVAS, and the canvas follows the window's aspect ratio rather than its
     * height. Every line is a step a reader can check:
     *
     *   halfH        the frustum's half-height at the sphere's plane, in world units
     *   pxPerWorld   how many pixels one world unit covers on this canvas
     *   D            the sphere's DRAWN DIAMETER in pixels, which is the figure the brief specifies
     *   cx, cy       where the brief wants the sphere's centre, in container pixels
     *   gx, gy       the group offset that puts it there
     */
    const applyLayout = () => {
      const s = side()
      /* 🔴 H AND W ARE MEASURED FROM THE CONTAINER, NEVER ASSUMED. `host` is `.aa-splash-globe`, which
         is `inset: 0` of the splash, so its client box IS the container the brief means. The previous
         round's absolute pixel target assumed a 1080 px viewport and the real container is about 924,
         which is the whole reason this is a ratio now. */
      const vw = Math.max(1, host.clientWidth)
      const vh = Math.max(1, host.clientHeight)

      const D = narrow ? NARROW_FRAME.diameterOfW * vw : FRAME.diameterOfH * vh
      const cx = (narrow ? NARROW_FRAME.centreOfW : FRAME.centreOfW) * vw
      const cy = (narrow ? NARROW_FRAME.centreOfH : FRAME.centreOfH) * vh

      /* THE CAMERA IS DERIVED FROM THE MEASURED HEIGHT, in three steps, each checkable:
           the sphere's radius is 1 world unit and must be D/2 pixels
           the frustum's half-height at the sphere's plane is therefore (side/2) / pxPerWorld
           and the distance that produces that half-height at this fov is halfH / tan(fov/2)
         Recomputed from the ResizeObserver, so the ratio holds at every window size. */
      const pxPerWorld = D / 2
      const halfH = s / 2 / pxPerWorld
      const cameraZ = halfH / HALF_TAN
      /* THE SOLVED DISTANCE IS REMEMBERED, and what the camera actually gets is that distance with the
         launch sequence's push-in applied. One statement owns `camera.position.z` and it is this one:
         the dolly setter below re-enters through `applyCamera()` rather than writing z itself, so a
         resize during the sequence keeps both the framing and the push-in. */
      solvedZ = cameraZ
      applyCamera()

      /* The canvas is `left: 0` and vertically centred on the viewport, which is the whole of what the
         stylesheet decides. So its centre in viewport coordinates is: */
      const canvasCx = s / 2
      const canvasCy = vh / 2

      const gx = (cx - canvasCx) / pxPerWorld
      /* Negated because screen y runs down and world y runs up. */
      const gy = -(cy - canvasCy) / pxPerWorld
      globe.position.set(gx, gy, 0)
      /* 🔴 THE LATTICE MOVES WITH THE PLANET. The brief: "Keep the particle lattice locked to the globe
         so it reframes together and doesn't drift out of alignment." Same offset, set in the adjacent
         statement, so there is no path through this function that moves one and not the other, and its
         aim and guard are recomputed below from the same pxPerWorld. */
      funnelGroup.position.set(gx, gy, 0)

      /* 🔴 PUBLISH WHAT WAS SOLVED, so a probe can measure the composition instead of re-deriving it.
         `testing/shot_hero.py` was reporting the CANVAS box as though it were the sphere, which since
         the canvas started covering the viewport meant "0 % cropped" for a globe that is visibly
         cropped. A second copy of this arithmetic in the probe would be a second thing to keep in
         step; the applied values are the honest thing to report. Same pattern as `--aa-scrollport`,
         published from a ResizeObserver so the stylesheet reads a measured height rather than
         guessing one. */
      if (el.dataset.aaDolly === undefined) el.dataset.aaDolly = '0'
      el.dataset.aaSphere = [
        Math.round(cx - D / 2),          // left limb, px from the viewport's left edge
        Math.round(cy - D / 2),          // top limb
        Math.round(D),                   // drawn diameter
        Math.round(vw),                  // W, measured from the container
        Math.round(vh),                  // H, measured from the container
        Math.round(cameraZ * 100) / 100, // the DERIVED camera distance
        Math.round(FUNNEL.startOfWidth * vw), // the lattice's apex, so a probe can confirm it
                                              // reframed with the planet rather than drifting
      ].join(',')

      /* ---- THE FUNNEL'S OWN GEOMETRY, in the group's coordinates, so relative to the sphere's centre.
         🔴 THE GUARD IS THE POINT HERE. The brief: "Keep the left 38% of the viewport completely free
         of particles." Two independent mechanisms, because one of them is a placement and the other is
         a guarantee:
           1. the lattice STARTS to the right of the guard, so in normal operation nothing is there;
           2. the shader fades any dot whose projected position falls left of it to zero anyway, so a
              resize, a drag or a future change to the shape cannot push the mesh into the type. */
      if (funnel) {
        const guardPx = FUNNEL.guardOfWidth * vw
        const startPx = FUNNEL.startOfWidth * vw
        const startWorld = (startPx - canvasCx) / pxPerWorld - gx
        /* Ends just inside the left surface, so the sheet arrives ON the limb and curves across it
           rather than stopping short in empty space. */
        funnel.aim(startWorld, FUNNEL.endWorld)
        /* The guard is handed over in NDC, because that is the space the vertex shader can test in
           without knowing anything about the viewport. The canvas is left-aligned and `s` wide, so a
           viewport x of `guardPx` is at canvas fraction guardPx/s, i.e. NDC 2*(guardPx/s) - 1. */
        funnel.guard((2 * guardPx) / s - 1)
      }
    }
    applyLayout()

    /* ---- THE FRAME LOOP.
       Own rAF rather than GSAP's ticker, and that is a decision this project has already paid for
       once: trap 5b.13 measured GSAP's clock failing to advance under the conditions the verifiers
       run in, and a globe that stops turning because a tween engine stalled is a puzzling failure
       rather than a visible one. rAF also stops when the tab is hidden, which is what a decorative
       WebGL surface should do.
       A REAL CLOCK, not a per-frame constant: `delta` means the rotation is the same speed on a
       144 Hz panel as on a 60 Hz one. Adding a fixed step per frame would spin it 2.4x faster on the
       better screen. */
    const clock = new THREE.Clock()
    let elapsed = 0
    let raf = 0
    let dragging: number | null = null
    let lastX = 0
    let lastY = 0
    let spinning = true
    /** How far the reader has dragged the tilt, clamped so the pole cannot come into shot. */
    let tilted = 0
    /** Timers that end the static-mode settle, so teardown can clear them. Empty in the live mode. */
    const settle: number[] = []

    const draw = () => {
      const d = clock.getDelta()
      elapsed += d
      if (spinning) {
        earth.rotation.y += SPIN * d
        if (clouds) clouds.rotation.y += CLOUD_SPIN * d
      }
      funnel?.update(elapsed)
      renderer.render(scene, camera)
      raf = requestAnimationFrame(draw)
    }

    /* 🔴 REDUCED MOTION AND NARROW RENDER ONE FRAME AND STOP, rather than looping over a static
       scene. Looping would burn a GPU on an unchanging image for a reader who asked for less, which
       is the opposite of honouring the preference.
       The textures arrive after this call, so a single render would draw a black sphere. The loading
       manager's `onLoad` fires once every queued texture has decoded, which is the signal rather than
       a timer; two bounded extra frames cover a texture that lands between the manager firing and the
       browser uploading it. */
    if (reduced || narrow) {
      /* A fixed time, so the funnel (where it exists) is a still frame of the field rather than
         everything sitting at t = 0, which would put every particle at the convergence point. */
      funnel?.update(6.5)
      const once = () => renderer.render(scene, camera)
      once()
      manager.onLoad = once
      settle.push(window.setTimeout(once, 400), window.setTimeout(once, 1600))
    } else {
      raf = requestAnimationFrame(draw)
    }

    /* ---- DRAG TO ROTATE, kept from the previous version because it is a real affordance and nothing
       in the brief asks for it to go.
       ⚠ THE WHEEL ZOOM IS GONE, DELIBERATELY. The framing is now the effect: the brief says the crop
       "is a large part of the cinematic effect", and a zoom control whose first turn shrinks the globe
       back inside the frame undoes it. Rotation cannot break the composition; scale can. */
    const onPointerDown = (e: PointerEvent) => {
      dragging = e.pointerId
      lastX = e.clientX
      lastY = e.clientY
      spinning = false
      el.setPointerCapture(e.pointerId)
      el.style.cursor = 'grabbing'
    }
    const onPointerMove = (e: PointerEvent) => {
      if (dragging === null) return
      /* Divided by the drawn size, so the same gesture turns the globe by the same amount whatever
         the viewport is. */
      const k = 2.4 / Math.max(1, side())
      const dx = (e.clientX - lastX) * k
      earth.rotation.y += dx
      if (clouds) clouds.rotation.y += dx
      /* On the GROUP, not on the scene: tilting the scene would tilt the funnel and the light with
         it, and the funnel is a stream arriving from off-frame rather than part of the planet. */
      tilted = Math.max(-0.5, Math.min(0.5, tilted + (e.clientY - lastY) * k))
      globe.rotation.x = tilted
      lastX = e.clientX
      lastY = e.clientY
      if (reduced || narrow) renderer.render(scene, camera)
    }
    const onPointerUp = (e: PointerEvent) => {
      if (dragging === null) return
      try {
        el.releasePointerCapture(e.pointerId)
      } catch {
        /* the capture may already have been lost; releasing twice is not worth surfacing */
      }
      dragging = null
      spinning = true
      el.style.cursor = 'grab'
    }

    el.style.cursor = 'grab'
    el.addEventListener('pointerdown', onPointerDown)
    el.addEventListener('pointermove', onPointerMove)
    el.addEventListener('pointerup', onPointerUp)
    el.addEventListener('pointercancel', onPointerUp)

    /* ---- RESIZE. Everything about the composition depends on the viewport, so this re-solves it
       rather than only resizing the buffer. Observes the HOST (the viewport-sized wrapper) as well as
       the canvas, because the canvas is sized off `vh` and a height change moves both. */
    const onResize = () => {
      const s = side()
      /* The ratio is recomputed, not just the size: the buffer cap is an AREA budget, so a window
         drag that doubles the element has to lower the ratio or the budget is a one-time claim rather
         than a guarantee. */
      renderer.setPixelRatio(ratioFor(s))
      renderer.setSize(s, s, false)
      applyLayout()
      if (reduced || narrow) renderer.render(scene, camera)
    }
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(onResize) : null
    ro?.observe(el)
    ro?.observe(host)

    /* ---- TEARDOWN. 🔴 EVERY ONE OF THESE LINES IS LOAD-BEARING AND THE BRIEF IS RIGHT THAT THREE.JS
       LEAKS BADLY WITHOUT THEM. Geometries and materials hold GPU buffers the garbage collector
       cannot see, textures hold decoded bitmaps, and the renderer holds the WebGL context itself.
       THE CONTEXT IS THE ONE THAT BITES. Chrome allows about 16 live contexts and this page already
       has one for the MapLibre map; leaking one per splash mount is how the map silently stops
       rendering later in a session. `dispose()` releases three's own state and `forceContextLoss()`
       is what actually hands the context back rather than waiting for the canvas to be collected. */
    return () => {
      el.removeEventListener('pointerdown', onPointerDown)
      el.removeEventListener('pointermove', onPointerMove)
      el.removeEventListener('pointerup', onPointerUp)
      el.removeEventListener('pointercancel', onPointerUp)
      ro?.disconnect()
      unregisterDolly()
      if (raf) cancelAnimationFrame(raf)
      for (const t of settle) window.clearTimeout(t)
      /* The manager is this effect's own object, so dropping the callback is enough: nothing outside
         holds a reference to it. */
      manager.onLoad = () => {}

      earthGeo.dispose()
      earthMat.dispose()
      cloudGeo?.dispose()
      cloudMat?.dispose()
      atmoGeo.dispose()
      atmoMat.dispose()
      funnel?.dispose()
      for (const t of textures) t.dispose()
      scene.clear()
      renderer.dispose()
      renderer.forceContextLoss()
    }
  }, [reduced, narrow])

  return (
    <div className="aa-splash-globe" ref={wrap} aria-hidden="true">
      {/* aria-hidden with no text alternative: it is scenery. Every fact it gestures at is stated in
          words on the screen in front of it. */}
      <canvas ref={canvas} className="aa-splash-globe-canvas" />
    </div>
  )
}
