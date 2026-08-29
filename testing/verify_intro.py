# -*- coding: utf-8 -*-
"""The cinematic intro: does the gate work, and can it never block the product?

    python testing/verify_intro.py

ZERO API CALLS. Everything here is the built bundle served from disk.

WHAT THIS FILE IS ACTUALLY GUARDING
-----------------------------------
An enter gate is a full-viewport overlay at z-index 200 over a working product. The failure that
matters is not "the animation looked wrong", it is "the overlay ate the click that reaches the rest
of the application". `verify_app_flow.py` runs with `?motion=off` precisely so it never meets the
gate, which means nothing else in the suite would notice if the gate started blocking Configure
forever. This file is where that is checked, WITH motion on.

So the checks are about contract, not choreography:

  * with motion on, the gate exists and carries its required parts, including a LOADED FortyGuard
    mark with its own per-theme correction (the banner's lives on `.aa-banner img` and does not
    reach here, which is how that logo washed out in light mode once already);
  * with `?motion=off`, nothing from intro/ mounts AT ALL and the point over the Configure button
    hits the button -- measured with elementFromPoint, not assumed from the absence of a node;
  * Enter UNMOUNTS the gate rather than leaving it at opacity 0, because an invisible sheet swallows
    clicks exactly as well as a visible one;
  * the audio contract holds: play attempted on both files with sound on, NEVER attempted with
    `?audio=off`, volume never above the 0.4 master, and pause+load (a real unload) on leaving the
    landing stage;
  * a narrow viewport and `prefers-reduced-motion` both skip the gate entirely;
  * the intro's body attribute is present on the landing stage and gone after it, which is what
    scopes every rule in intro.css to one stage of a single-document app.

HOW THE AUDIO IS OBSERVED. `audio.ts` builds its elements with `new Audio()`, so they are never in
the DOM and cannot be found with a selector. The probe instead patches
`HTMLMediaElement.prototype.play / pause / load` and the `volume` setter BEFORE the bundle runs --
possible because Vite emits the app as `type="module"`, which is deferred, while a classic inline
script in <head> executes during parse. Every call is recorded with its src.
"""
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AA = os.path.join(ROOT, "AGENTIC-ARBITER")
DIST = os.path.join(AA, "app", "dist")
AUDIO_DIR = os.path.join(AA, "demo", "audio")
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

FACILITY = "metro_ashburn"
CHECKS = []


def ck(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("   %s %s%s" % ("PASS" if ok else "FAIL", label, ("   " + detail) if detail else ""))


def head(t):
    print()
    print("   " + t)
    print("   " + "-" * (len(t) + 2))


PROBE = r"""
<script>
/* Runs during parse, before the deferred module bundle. Patches media so audio built with
   `new Audio()` -- never in the DOM -- can still be observed. */
(function(){
  var M = {play: [], pause: [], load: [], maxVolume: 0, muted: []};
  window.__aaMedia = M;
  var P = HTMLMediaElement.prototype;
  var _play = P.play, _pause = P.pause, _load = P.load;
  function name(el){
    /* THE ATTRIBUTE, NOT THE PROPERTY. `el.src = ''` is resolved against the document, so reading
       `el.src` back on a torn-down element returns the PAGE's url and looks like a real source.
       The attribute is the honest record of what was asked for. */
    var s = el.getAttribute ? el.getAttribute('src') : null;
    if (!s) return 'cleared';
    /* .mp3 OR .wav: the swell became a WAV in step 6 (there is no MP3 encoder on the build machine)
       and an extension-specific pattern reported it as 'cleared' -- a real file read as a torn-down
       one, which failed the product for a change in the probe. */
    var m = /([^\/]+\.(?:mp3|wav))/.exec(s);
    return m ? m[1] : 'cleared';
  }
  P.play  = function(){ M.play.push(name(this));  return _play.apply(this, arguments); };
  P.pause = function(){ M.pause.push(name(this)); return _pause.apply(this, arguments); };
  P.load  = function(){ M.load.push(name(this));  return _load.apply(this, arguments); };
  var vd = Object.getOwnPropertyDescriptor(P, 'volume');
  if (vd && vd.set) {
    Object.defineProperty(P, 'volume', {
      configurable: true,
      get: function(){ return vd.get.call(this); },
      set: function(v){ if (v > M.maxVolume) M.maxVolume = v; return vd.set.call(this, v); }
    });
  }
  var md = Object.getOwnPropertyDescriptor(P, 'muted');
  if (md && md.set) {
    Object.defineProperty(P, 'muted', {
      configurable: true,
      get: function(){ return md.get.call(this); },
      set: function(v){ M.muted.push(!!v); return md.set.call(this, v); }
    });
  }
})();
</script>
<script>
/* The scenario driver. Which one runs is the URL hash. */
(function(){
  var SC = (location.hash || '#observe').slice(1);
  var out = {scenario: SC, steps: [], err: null};

  function q(s){ return document.querySelector(s); }
  function txt(s){ var e = q(s); return e ? (e.textContent || '').trim() : null; }
  function findBtn(re){
    var b = document.querySelectorAll('button, a');
    for (var i = 0; i < b.length; i++) if (re.test(b[i].textContent || '')) return b[i];
    return null;
  }

  /* 🔴 CONTRAST, MEASURED IN THE BROWSER, because the same token passes in one theme and fails in
     the other. --fg-bright is 6.83:1 on the dark page and was 4.27:1 on the light one, and an
     `opacity: 0.72` on the note put it at 3.71:1. Neither is visible by reading the CSS.
     Composites the text colour's alpha AND every inherited opacity over the nearest opaque
     background, then applies the WCAG relative-luminance formula. */
  function _rl(rgb){
    var s = rgb.map(function(v){ v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * s[0] + 0.7152 * s[1] + 0.0722 * s[2];
  }
  function _parse(c){
    var m = /rgba?\(([^)]+)\)/.exec(c || '');
    if (!m) return null;
    var p = m[1].split(',').map(parseFloat);
    return {rgb: [p[0], p[1], p[2]], a: p.length > 3 ? p[3] : 1};
  }
  /* #rrggbb / #rgb, which is how the component declares its fill. */
  function _hex(h){
    var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(h.trim());
    if (!m) return null;
    var v = m[1];
    if (v.length === 3) v = v[0]+v[0]+v[1]+v[1]+v[2]+v[2];
    return [parseInt(v.slice(0,2),16), parseInt(v.slice(2,4),16), parseInt(v.slice(4,6),16)];
  }
  function _bg(el){
    var e = el;
    while (e) {
      var v = _parse(getComputedStyle(e).backgroundColor);
      if (v && v.a > 0.98) return v.rgb;
      e = e.parentElement;
    }
    return [9, 9, 11];
  }
  function contrast(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var cs = getComputedStyle(el);
    var f = _parse(cs.color);
    /* 🔴 A COLOUR THIS CANNOT READ IS REPORTED AS A FAILURE, NOT DROPPED. A `color-mix()` computes
       to `oklab(...)`, which the regex above does not match; returning null filtered the row out of
       the results entirely and the element went unmeasured while everything still said PASS. Only
       the "six elements measured" count caught it. Now the row survives with ratio 0 and carries the
       value it could not parse. */
    if (!f) return {sel: sel, ratio: 0, size: cs.fontSize, weight: cs.fontWeight,
                    unparsed: cs.color};
    /* Own opacity, then every ancestor's: opacity multiplies down the tree. */
    var e = el;
    while (e) {
      var o = parseFloat(getComputedStyle(e).opacity);
      if (!isNaN(o) && o < 1) f.a *= o;
      e = e.parentElement;
    }
    /* 🔴 A GRADIENT FILL IS INVISIBLE TO `background-color`, and that produced a false failure.
       ShinyButton's fill is `linear-gradient(var(--shiny-cta-bg), var(--shiny-cta-bg)) padding-box`
       plus a conic border, so its computed `background-color` is transparent and _bg() walked past it
       to the page. In the light theme that put white text on a near-white page and measured 1.10:1 --
       for a button that renders white on #101826, which is 17.9:1.
       The component declares its own fill as a custom property, so that is what to measure against.
       Read from the element rather than from the stylesheet, so a theme override is picked up. */
    var own = cs.getPropertyValue('--shiny-cta-bg').trim();
    var bg = own ? (_parse(own) ? _parse(own).rgb : _hex(own)) : _bg(el);
    if (!bg) bg = _bg(el);
    var comp = [0, 1, 2].map(function(i){ return f.rgb[i] * f.a + bg[i] * (1 - f.a); });
    var l1 = _rl(comp), l2 = _rl(bg);
    var hi = Math.max(l1, l2), lo = Math.min(l1, l2);
    return {sel: sel, ratio: Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100,
            size: cs.fontSize, weight: cs.fontWeight};
  }

  function snapshot(tag){
    var gate = q('.aa-gate');
    var cfg = findBtn(/Configure this plant/);
    /* 🔴 WHAT THIS ACTUALLY HAS TO ANSWER: is a full-viewport overlay covering the page?
       The first version probed the centre of the Configure button, and once the agent-loop diagram
       was added that button moved below a 940px viewport, so the probe returned "offscreen" and the
       check failed for a reason that had nothing to do with overlays.
       So: probe the button when it is on screen, and fall back to the CENTRE OF THE VIEWPORT when it
       is not. Either point answers the real question -- the gate is `inset: 0`, so if it is
       intercepting anything it is intercepting both. `hitProbe` records which point was used, so a
       pass can never be mistaken for the other measurement. */
    var hit = null, hitBlocked = null, hitProbe = null;
    var cx = null, cy = null;
    if (cfg) {
      var r = cfg.getBoundingClientRect();
      var bx = Math.round(r.left + r.width / 2), by = Math.round(r.top + r.height / 2);
      if (by >= 0 && by <= innerHeight && bx >= 0 && bx <= innerWidth) {
        cx = bx; cy = by; hitProbe = 'configure-button';
      }
    }
    if (cx === null) {
      cx = Math.round(innerWidth / 2); cy = Math.round(innerHeight / 2);
      hitProbe = 'viewport-centre';
    }
    var el = document.elementFromPoint(cx, cy);
    hit = el ? (el.tagName.toLowerCase()
                + (el.id ? '#' + el.id : '')
                + (el.className && typeof el.className === 'string'
                    ? '.' + el.className.trim().split(/\s+/)[0] : '')) : 'none';
    /* Blocked means the gate, or something inside it, is what the point lands on. */
    hitBlocked = !!(gate && el && (el === gate || gate.contains(el)));
    return {
      tag: tag,
      t: Math.round(performance.now()),
      stage: document.body.dataset.stage || null,
      introAttr: document.body.getAttribute('data-aa-intro'),
      gatePresent: !!gate,
      gateOpacity: gate ? getComputedStyle(gate).opacity : null,
      /* THE TRANSITION AS DECLARED, because the animated VALUE is not reliably observable here:
         `--virtual-time-budget` advances Chrome's clock in jumps, so a sample taken "mid
         transition" can read the start or the end rather than a value in between. What is stable
         and still proves the fade is (a) the element is mounted and carrying is-leaving well after
         the click, and (b) opacity is actually a transitioned property with the 600 ms duration the
         brief asks for. Together those are the fade; a sampled 0.37 would only be prettier. */
      gateTransitionProperty: gate ? getComputedStyle(gate).transitionProperty : null,
      gateTransitionDuration: gate ? getComputedStyle(gate).transitionDuration : null,
      gateLeaving: gate ? gate.classList.contains('is-leaving') : null,
      gateTitle: txt('#aa-gate-title'),
      gateSub: txt('.aa-gate-sub'),
      hasEnter: !!q('.shiny-cta'),
      enterLabel: (function(){
        var b = q('.shiny-cta'); return b ? (b.textContent || '').trim() : null; })(),
      enterAria: (function(){
        var b = q('.shiny-cta'); return b ? b.getAttribute('aria-label') : null; })(),
      /* THE TOGGLE IS GONE FROM THE SPLASH BY INSTRUCTION ("Remove any existing Sound on toggle
         buttons from this page"), so its ABSENCE is what is asserted now. The persistent corner
         toggle is a different surface and is still checked separately. */
      hasGateMute: !!q('.aa-gate-mute'),
      /* THE GLOBE. cobe draws to a canvas; if it never mounted there is nothing to drag. */
      globeCanvas: (function(){
        var c = q('.aa-splash-globe-canvas');
        if (!c) return null;
        var r = c.getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height),
                square: Math.abs(r.width - r.height) < 2,
                hasGL: !!(c.getContext && (c.getContext('webgl') || c.getContext('webgl2')))};
      })(),
      /* THE FIVE STAGE ROWS ARE GONE FROM THE PAGE ENTIRELY, removed 2026-08-29 at the user's
         instruction ("remove this", with a screenshot of the section). They had been moved out of the
         splash to below the map earlier the same day, so this counts them ANYWHERE rather than in
         either place: the assertion is an absence, and an absence has to be global to mean anything.
         Both class families are counted, because the rows carried `.aa-splash-widget` in the hero and
         `.aa-stagerow` below the map. */
      stageRowsAnywhere:
        document.querySelectorAll('.aa-stagerow, .aa-stagerows, .aa-splash-widget').length,
      hasPersistentMute: !!q('.aa-mutebtn'),
      /* THE MARK IS CHECKED FOR HAVING LOADED, not just for being in the DOM. `naturalWidth` is 0
         for a broken src, which is the only failure mode that matters here: the path resolves at
         /app/ through ART and at the demo root, and an <img> with a bad src renders as nothing
         while the element itself still passes every selector-based check. */
      brandPresent: !!q('.aa-gate-brand'),
      brandLabel: txt('.aa-gate-by'),
      logoNaturalWidth: (function(){
        var i = q('.aa-gate-brand img'); return i ? i.naturalWidth : null; })(),
      logoSrc: (function(){
        var i = q('.aa-gate-brand img');
        return i ? (i.getAttribute('src') || '') : null; })(),
      logoAlt: (function(){
        var i = q('.aa-gate-brand img'); return i ? i.getAttribute('alt') : null; })(),
      logoFilter: (function(){
        var i = q('.aa-gate-brand img');
        return i ? getComputedStyle(i).filter : null; })(),
      logoHeight: (function(){
        var i = q('.aa-gate-brand img');
        return i ? Math.round(i.getBoundingClientRect().height) : null; })(),
      noteGone: !document.querySelector('.aa-gate-note'),
      /* THE HERO. `heroMs` is the duration GSAP actually built, published by timeline.ts onto the
         body, so "under 1.6 s" is read from the engine rather than added up by hand. */
      heroMs: document.body.dataset.aaHeroMs ? Number(document.body.dataset.aaHeroMs) : null,
      /* 🔴 EVERY TARGET IS REPORTED WHETHER OR NOT IT WAS FOUND, and that is a correction.
         This used to write a key only `if (el)`, so a selector that stopped matching produced no entry,
         the Python side looped over what was there, and the checks for that target simply DISAPPEARED.
         It happened: the headline's four paragraphs became list items, `SEL.prose` still said `> p`,
         the lines dropped out of the hero reveal, and the only symptom was the total falling from 208
         to 204 with nothing red. Gotcha #74 in a new costume -- a check that does not run reports
         success.
         Now a missing target lands as `{found: false}` and section 9 fails on it by name. */
      heroSel: {
        eyebrow: '[data-aa-hero="eyebrow"]', headline: '[data-aa-hero="headline"]',
        prose: '[data-aa-hero="prose"] > ul > li', status: '[data-aa-hero="status"]',
        cta: '[data-aa-hero="cta"]'
      },
      hero: ['eyebrow', 'headline', 'prose', 'status', 'cta'].reduce(function(o, k){
        var sel = k === 'prose' ? '[data-aa-hero="prose"] > ul > li'
                                : '[data-aa-hero="' + k + '"]';
        var el = document.querySelector(sel);
        if (!el) { o[k] = {found: false, sel: sel}; return o; }
        var c = getComputedStyle(el);
        o[k] = {found: true, op: c.opacity, tr: c.transform || 'none'};
        return o;
      }, {}),
      brandStyle: (function(){
        var e = document.querySelector('.aa-banner-brand');
        if (!e) return null;
        var c = getComputedStyle(e); return {op: c.opacity, tr: c.transform || 'none'};
      })(),
      /* SplitText's runtime wrappers. Any left behind means the DOM a reader, a screen reader or a
         later check sees is not the DOM this project ships. */
      /* THE AGENT LOOP. Five stages, their labels, the return arc, the pulse and whether the
         ambient loops are running -- the last read from body[data-aa-ring], which timeline.ts
         publishes so the pulse's visibility can be CSS-gated. */
      ring: (function(){
        var root = document.querySelector('[data-aa-hero="ring"]');
        if (!root) return null;
        var nodes = Array.prototype.map.call(
          root.querySelectorAll('.aa-ring-node'), function(g){
            var lab = g.querySelector('.aa-ring-label');
            var note = g.querySelector('.aa-ring-note');
            var halo = g.querySelector('.aa-ring-halo');
            var cs = getComputedStyle(g);
            return {
              key: g.getAttribute('data-aa-node'),
              label: lab ? (lab.textContent || '').trim() : null,
              note: note ? (note.textContent || '').trim() : null,
              noteOpacity: note ? Number(getComputedStyle(note).opacity) : null,
              haloOpacity: halo ? Number(getComputedStyle(halo).opacity) : null,
              groupOpacity: cs.opacity,
              transform: cs.transform || 'none'
            };
          });
        var pulse = root.querySelector('[data-aa-pulse]');
        var track = root.querySelector('#aa-ring-track');
        return {
          present: true,
          displayed: getComputedStyle(root).display !== 'none',
          nodes: nodes,
          returnLabel: (function(){
            var t = root.querySelector('.aa-ring-return');
            return t ? (t.textContent || '').trim() : null; })(),
          hasArrow: !!root.querySelector('.aa-ring-arrow'),
          trackOpacity: track ? getComputedStyle(track).opacity : null,
          pulseVisibility: pulse ? getComputedStyle(pulse).visibility : null,
          pulseTransform: pulse ? (getComputedStyle(pulse).transform || 'none') : null,
          srText: (function(){
            var p = root.querySelector('.aa-ring-sr');
            return p ? (p.textContent || '').trim().slice(0, 60) : null; })(),
          running: document.body.dataset.aaRing || null
        };
      })(),
      /* THE HEAT FIELD. Reported in every snapshot because the requirement that matters most is a
         NEGATIVE one -- it must not exist on the configure or results screens -- and that is only
         observable after the stage has changed. */
      thermal: (function(){
        var t = document.querySelector('.aa-thermal');
        if (!t) return null;
        var cs = getComputedStyle(t);
        var a = t.querySelector('.aa-thermal-a'), b = t.querySelector('.aa-thermal-b');
        function an(x){
          if (!x) return null;
          var c = getComputedStyle(x);
          return {name: c.animationName, dur: c.animationDuration,
                  dir: c.animationDirection, iter: c.animationIterationCount,
                  moved: (c.transform || 'none') !== 'none'};
        }
        var app = document.getElementById('app');
        var head = document.querySelector('[data-aa-hero="headline"]');
        var over = null;
        if (head) {
          var hr = head.getBoundingClientRect();
          var el = document.elementFromPoint(Math.round(hr.left + 20),
                                            Math.round(hr.top + hr.height / 2));
          over = !!(el && (el === t || t.contains(el)));
        }
        return {
          parentIsBody: t.parentElement === document.body,
          position: cs.position,
          zIndex: cs.zIndex,
          opacity: Number(cs.opacity),
          pointerEvents: cs.pointerEvents,
          appZIndex: app ? getComputedStyle(app).zIndex : null,
          coversContent: over,
          a: an(a),
          b: an(b)
        };
      })(),
      /* The banner's FortyGuard mark, so a regression in its per-theme correction is caught here
         rather than in a screenshot. It has been reported washed out once already. */
      bannerLogo: (function(){
        var i = document.querySelector('.aa-banner img');
        if (!i) return null;
        var c = getComputedStyle(i);
        return {opacity: c.opacity, filter: c.filter, h: Math.round(i.getBoundingClientRect().height)};
      })(),
      splitWrappers: document.querySelectorAll('.aa-hero-line').length,
      maskDivs: document.querySelectorAll('[data-aa-hero="headline"] > div').length,
      headlineHTML: (function(){
        var h = document.querySelector('[data-aa-hero="headline"]');
        return h ? h.innerHTML : null;
      })(),
      configureFound: !!cfg,
      configureHit: hit,
      configureBlocked: hitBlocked,
      configureHitProbe: hitProbe,
      /* Where the CTA sits relative to the fold. Not an assertion -- a fact worth reporting, since
         the diagram added real height above it. */
      ctaTop: cfg ? Math.round(cfg.getBoundingClientRect().top) : null,
      viewportH: window.innerHeight,
      theme: document.documentElement.dataset.theme || null,
      /* ONE contrast list again. There were two while the stage rows lived on the page, because the
         splash is pinned dark in both themes and the page follows the reader's theme, so the same
         token could pass in one and fail in the other. With the rows removed there is one surface
         left to measure. */
      contrast: ['.aa-gate-eyebrow', '.aa-gate-title', '.aa-gate-sub', '.aa-gate-by',
                 '.shiny-cta'].map(contrast).filter(Boolean),
      media: JSON.parse(JSON.stringify(window.__aaMedia || {}))
    };
  }

  function publish(){
    var d = document.createElement('div');
    d.id = 'INTROPROBE'; d.style.display = 'none';
    d.textContent = JSON.stringify(out);
    document.body.appendChild(d);
  }

  function waitFor(test, ms, then){
    var t0 = performance.now();
    var iv = setInterval(function(){
      if (test() || performance.now() - t0 > ms) { clearInterval(iv); then(); }
    }, 100);
  }

  function run(){
    try {
      if (SC === 'observe') {
        out.steps.push(snapshot('settled'));
        publish(); return;
      }
      if (SC === 'enter') {
        /* 🔴 THE LOCK IS MEASURED AS A COMPUTED STYLE, NOT BY TRYING TO SCROLL, and the first
           version of this got it wrong in a way worth recording. It called
           `window.scrollTo(0, 900)` and reported the page had moved to 501 -- but
           `overflow: hidden` blocks USER scrolling (wheel, touch, keys) while Chrome still honours
           a PROGRAMMATIC scroll. So the probe was scrolling a page a reader cannot scroll, and then
           failing the product for it. A synthetic `wheel` event is no better: untrusted events do
           not scroll in Chrome.
           What is both true and checkable is the lock itself: the ROOT element's overflow, which is
           the only one that propagates to the viewport, plus the fact that it is put back. */
        out.htmlOverflowGateUp = getComputedStyle(document.documentElement).overflowY;
        out.bodyOverflowGateUp = getComputedStyle(document.body).overflowY;
        out.docScrollHeight = Math.round(document.documentElement.scrollHeight);
        out.scrollBefore = Math.round(scrollY);

        out.steps.push(snapshot('before-enter'));
        var e = q('.shiny-cta');
        if (!e) { out.err = 'no Enter button to click'; publish(); return; }
        e.click();
        /* MID-FADE. The first version of this check only looked after 1200 ms, which is true
           whether the card faded or vanished -- and it HAD been vanishing, in one React commit,
           because the unmount batched with the class change. 250 ms is comfortably inside a 600 ms
           transition and comfortably outside the first frame. */
        setTimeout(function(){ out.steps.push(snapshot('mid-fade')); }, 250);
        /* THE LAUNCH SEQUENCE MADE THIS WINDOW MUCH LONGER. The click used to unmount the gate
           640 ms later; it now starts a timed cinematic whose length is derived from the measured
           voiceover (4.676 + 1.0 hold + 1.2 out = 6.876 s), and the watchdog in launch.ts
           completes it at +400 ms. So 'after-fade' moved from 1400 ms to 7600 and 'settled' from
           6200 to 13500, which also has to clear the HERO timeline's own watchdog: it
           is built when the sequence ends and fires total + WATCHDOG_MARGIN
           (1.52 + 0.7) later, about 9.5 s, and then its AMBIENT LOOPS start after that.
           11000 was measured as flaky against exactly that tail: one run in two failed on
           'the pulse is on screen'. A check that passes half the time is worse than no
           check, so the margin is now 4 s rather than 1.5. It costs nothing: under the
           virtual clock these are ordering constraints, not wall-clock seconds.
           GSAP DOES NOT ADVANCE UNDER VIRTUAL TIME (05-TRAPS 5b.13), so what actually completes
           the sequence in this harness is that wall-clock watchdog. That is a feature rather than
           a workaround: it is the same mechanism that protects a reader whose GSAP clock stalls,
           and this is the check that proves it fires. */
        setTimeout(function(){
          out.steps.push(snapshot('after-fade'));
          out.scrollAfterEnter = Math.round(scrollY);
          out.htmlOverflowAfter = getComputedStyle(document.documentElement).overflowY;
        }, 7600);
        /* 🔴 A SECOND, LATE SAMPLE, and the first version of the hero checks did not have one.
           They read `after-fade` at 1400 ms and failed the product for being mid-animation: the
           audio-synced timeline is 4110 ms and its watchdog deadline is 4810 ms, so 1400 ms is
           simply too early to ask "did it finish". 6200 ms is past both.
           The gate assertions keep using `after-fade`, because the gate really is gone by then. */
        setTimeout(function(){
          out.steps.push(snapshot('settled'));
          publish();
        }, 13500);
        return;
      }
      if (SC === 'leave') {
        var e2 = q('.shiny-cta');
        if (e2) e2.click();
        setTimeout(function(){
          out.steps.push(snapshot('on-landing'));
          var cfg = findBtn(/Configure this plant/);
          if (!cfg) { out.err = 'no Configure button'; publish(); return; }
          cfg.click();
          waitFor(function(){ return document.body.dataset.stage === 'configure'; }, 6000,
            function(){
              setTimeout(function(){ out.steps.push(snapshot('after-leaving')); publish(); }, 700);
            });
        }, 1500);
        return;
      }
      if (SC === 'handoff') {
        /* 🔴 DOWN AND BACK UP, because the bug this guards against was one-way.
           The two scroll tweens were pushed into the same array the handoff's own onUpdate PAUSES
           once the fade passes 90 %, so they paused themselves, froze, and could never reverse.
           MEASURED before the fix: correct to 0 at scrollY 360, then back UP to 0.060 at 480, and
           stuck at 0 after returning to the top -- a reader who scrolled down and up was left on a
           landing page with no background. Sampling only downwards would have passed. */
        var e4 = q('.shiny-cta');
        if (e4) e4.click();
        out.handoff = [];
        var seq = [0, 120, 240, 360, 480, 620, 360, 120, 0];
        var k = 0;
        setTimeout(function(){
          var hv = setInterval(function(){
            if (k >= seq.length) {
              clearInterval(hv);
              out.steps.push(snapshot('scrolled-back'));
              publish();
              return;
            }
            /* documentElement.scrollTop, NOT window.scrollTo: lib/noscrolljump.ts patches
               window.scrollTo and deliberately swallows a scroll-to-top when the stage has not
               changed, so the return leg of this sequence would silently not happen. */
            document.documentElement.scrollTop = seq[k];
            var y = seq[k];
            k++;
            setTimeout(function(){
              var t = q('.aa-thermal'), r = q('[data-aa-hero="ring"]');
              var tc = t ? getComputedStyle(t) : null, rc = r ? getComputedStyle(r) : null;
              out.handoff.push({
                y: y,
                scrollY: Math.round(scrollY),
                fade: tc ? Number(tc.getPropertyValue('--aa-th-fade')) : null,
                fieldOpacity: tc ? Number(tc.opacity) : null,
                ringOpacity: rc ? Number(rc.opacity) : null
              });
            }, 200);
          }, 420);
        }, 2600);
        return;
      }
      if (SC === 'align') {
        /* 🔴 IS ANY PART OF A NODE EVER DISPLACED FROM THE REST OF IT?
           A single snapshot cannot answer this: the fault only existed WHILE something was scaling,
           and it was found by eye in a screenshot rather than by any check. An SVG scale needs its
           origin stated, three different ways of stating it were tried, and only the third worked --
           so this samples continuously and reports the worst offset between each node's halo and its
           own disc. They are concentric by construction; any offset at all is a transform origin
           being wrong. */
        var e3 = q('.shiny-cta');
        if (e3) e3.click();
        out.align = {worst: 0, worstNode: null, samples: 0, perNode: {}};
        var iv = setInterval(function(){
          document.querySelectorAll('.aa-ring-node').forEach(function(g){
            var h = g.querySelector('.aa-ring-halo'), dd = g.querySelector('.aa-ring-disc');
            if (!h || !dd) return;
            var hr = h.getBoundingClientRect(), dr = dd.getBoundingClientRect();
            if (hr.width < 2) return;
            var off = Math.abs((hr.left + hr.width / 2) - (dr.left + dr.width / 2));
            var k = g.getAttribute('data-aa-node');
            out.align.samples++;
            if (!(k in out.align.perNode) || off > out.align.perNode[k]) {
              out.align.perNode[k] = Math.round(off * 100) / 100;
            }
            if (off > out.align.worst) {
              out.align.worst = Math.round(off * 100) / 100;
              out.align.worstNode = k;
            }
          });
        }, 60);
        setTimeout(function(){
          clearInterval(iv);
          out.steps.push(snapshot('aligned'));
          publish();
        }, 11000);
        return;
      }
      out.err = 'unknown scenario ' + SC;
      publish();
    } catch (e) { out.err = String(e) + ' | ' + (e.stack || '').slice(0, 240); publish(); }
  }

  /* Wait for the app to have rendered something real before acting. */
  var boot = setInterval(function(){
    if (!document.querySelector('button, a')) return;
    clearInterval(boot);
    setTimeout(run, 2600);
  }, 150);
})();
</script>
"""


def serve(hold="2"):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port),
                          "--hold", str(hold)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % port, timeout=1).read(1)
            break
        except Exception:
            time.sleep(0.4)
    return p, port


def load(port, query, scenario, size=(1400, 940), extra=(), page="_intro.html",
         realtime=False):
    """One headless load with a fresh profile. Returns the probe's dict, or None.

    🔴 `realtime` EXISTS BECAUSE ScrollTrigger DOES NOT ADVANCE UNDER VIRTUAL TIME.
    `--virtual-time-budget` is what lets every other scenario here finish in a fraction of the
    wall-clock time it describes, and it is also why GSAP's clock crawls: MEASURED, the scroll
    handoff reported --aa-th-fade of exactly 1 at every scroll position from 0 to 750, i.e. it never
    fired at all, while on a real clock the same code scrubbed correctly.
    So the handoff is measured with the budget REMOVED and the load event held open instead --
    serve_app.py's `--hold` keeps one subresource pending, which is what --dump-dom waits for. The
    page then runs on a real clock for as long as the hold lasts. Same trick the project already uses
    for its screenshots, same reason.
    """
    prof = tempfile.mkdtemp(prefix="intro_")
    url = "http://127.0.0.1:%d/app/%s?facility=%s%s#%s" % (port, page, FACILITY, query, scenario)
    clock = [] if realtime else ["--virtual-time-budget=30000"]
    try:
        r = subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
             "--user-data-dir=" + prof, "--window-size=%d,%d" % size,
             "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--autoplay-policy=no-user-gesture-required",
             *clock, "--dump-dom", *extra, url],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'id="INTROPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    return json.loads(m.group(1)) if m else None


def last(d, tag=None):
    if not d or not d.get("steps"):
        return {}
    if tag:
        for s in d["steps"]:
            if s.get("tag") == tag:
                return s
    return d["steps"][-1]


def main():
    print("=" * 78)
    print("THE CINEMATIC INTRO -- gate contract, kill switches, audio rules")
    print("=" * 78)

    # ------------------------------------------------------------------ files
    head("1. THE AUDIO FILES: self-hosted, real, and inside budget")
    total = 0
    # transition-whoosh.mp3 replaced the generated swell.wav in a user change on
    # 2026-08-29. audio.ts records the reasoning; this is the list that caught it.
    for n in ("voiceover.mp3", "transition-whoosh.mp3"):
        p = os.path.join(AUDIO_DIR, n)
        ok = os.path.isfile(p)
        ck(ok, "demo/audio/%s exists" % n, p if not ok else "")
        if not ok:
            continue
        b = io.open(p, "rb").read()
        total += len(b)
        if n.endswith(".wav"):
            ck(b[:4] == b"RIFF" and b[8:12] == b"WAVE",
               "%s is a real WAV" % n, b[:4].decode("latin-1"))
            # 🔴 AND IT IS NOT SILENCE. The whole point of step 6 is that these files carry audio;
            # both shipped as silent placeholders through steps 1 to 5, and a check that only looked
            # at the magic bytes passed the entire time. RMS is computed from the PCM directly.
            import array
            pcm = array.array("h")
            pcm.frombytes(b[44: 44 + ((len(b) - 44) // 2) * 2])
            rms = (sum(float(v) * v for v in pcm) / max(1, len(pcm))) ** 0.5 / 32768.0
            peak = max(abs(v) for v in pcm) / 32768.0 if len(pcm) else 0.0
            ck(rms > 0.05, "%s carries actual signal, not silence" % n,
               "rms %.3f, peak %.3f over %s samples" % (rms, peak, format(len(pcm), ",")))
            ck(peak <= 0.95, "and leaves headroom, so nothing clips before the 0.4 master",
               "peak %.3f" % peak)
        else:
            ck(b[:2] == b"\xff\xfb" or b[:3] == b"ID3",
               "%s is a real MP3 stream" % n, " ".join("%02X" % c for c in b[:3]))
            # No decoder here, so "not silence" is judged the only way available: the silent
            # placeholder was 104-byte frames of pure zero payload, 96 % zero bytes. Real speech is
            # nothing like that.
            zfrac = b.count(b"\x00") / float(len(b))
            ck(zfrac < 0.5, "%s is not the silent placeholder it replaced" % n,
               "%.1f%% zero bytes (the placeholder was 96.2%%)" % (100.0 * zfrac))
    audio_src = io.open(os.path.join(AA, "app", "src", "intro", "audio.ts"),
                        encoding="utf-8").read()
    ck("audio/voiceover.mp3" in audio_src and "audio/transition-whoosh.mp3" in audio_src,
       "and the app fetches both through ART, so they resolve at /app/ and at the demo root")
    ck("audio/swell.mp3" not in audio_src,
       "with no reference left to the placeholder that was removed")
    ck(0 < total <= 300 * 1024, "both together are inside the ~300 KB budget",
       "%s bytes (%.0f KB)" % (format(total, ","), total / 1024.0))

    if not os.path.isdir(DIST):
        print("\n   [skip] no build at AGENTIC-ARBITER/app/dist.")
        return 3

    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    io.open(os.path.join(DIST, "_intro.html"), "w", encoding="utf-8", newline="").write(
        src.replace("</head>", PROBE + "</head>"))
    # A THEME-SEEDED COPY FOR EACH PALETTE. The theme is resolved by an inline script in <head> that
    # reads localStorage BEFORE the bundle runs, so the only way to choose it for a fresh profile is
    # to write the key ahead of that script. A query parameter would be read too late.
    for theme in ("dark", "light"):
        seed = "<script>try{localStorage.setItem('aa-theme','%s')}catch(e){}</script>" % theme
        io.open(os.path.join(DIST, "_intro_%s.html" % theme), "w",
                encoding="utf-8", newline="").write(
            src.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + seed)
               .replace("</head>", PROBE + "</head>"))

    srv, port = serve()
    try:
        # -------------------------------------------------------------- gate on
        head("2. MOTION ON: the gate is there and carries its four required parts")
        d = load(port, "", "observe")
        s = last(d)
        ck(bool(d) and not d.get("err"), "the probe ran", (d or {}).get("err") or "")
        ck(s.get("gatePresent") is True, "the gate is present")
        ck((s.get("gateTitle") or "").replace("\u00b7", "-") == "AGENTIC-ARBITER",
           "it shows the product name", repr(s.get("gateTitle")))
        ck(bool(s.get("gateSub")), "one line of subtext", (s.get("gateSub") or "")[:52])
        ck(s.get("hasEnter") is True, "one entry button, the supplied ShinyButton")
        ck((s.get("enterLabel") or "") == "Initialize Arbiter",
           "labelled as the brief asks", repr(s.get("enterLabel")))
        ck("open the site map" in (s.get("enterAria") or ""),
           "and its accessible name says where it goes, since the visible label does not",
           repr(s.get("enterAria")))
        # 🔴 THE TOGGLE'S ABSENCE IS THE ASSERTION NOW. The user's instruction was "Remove any
        # existing Sound on toggle buttons from this page", which reverses their earlier "a small mute
        # toggle on the gate itself". Honoured literally: gone from here, kept in the corner after the
        # splash closes, which section 5 checks.
        ck(s.get("hasGateMute") is False,
           "no sound toggle on the splash, per the instruction that removed it")

        # THE GLOBE.
        g = s.get("globeCanvas") or {}
        ck(bool(g), "the heat globe mounted")
        ck(g.get("square") is True, "square, so the earth is not drawn as an oval",
           "%sx%s" % (g.get("w"), g.get("h")))
        ck((g.get("w") or 0) >= 240, "and large enough to be the focal point",
           "%s px" % g.get("w"))

        gate_src = io.open(os.path.join(AA, "app", "src", "intro", "IntroGate.tsx"),
                           encoding="utf-8").read()
        ck("aria-modal" in gate_src and "e.key !== 'Tab'" in gate_src,
           "the modal contains Tab, so it cannot hand focus to controls hidden behind it")
        ck("returnFocusTo" in gate_src,
           "and focus is restored to wherever it came from when the card goes")
        # 🔴 THE SPLASH NEVER WRITES AN AUDIO PREFERENCE AT ALL. Previously it stored the toggle's
        # value, and a per-load `?audio=off` therefore became permanent. With the toggle gone there is
        # no choice to record here, so the correct behaviour is to record nothing.
        ck("storeAudioChoice" not in gate_src,
           "and the splash writes no audio preference, so ?audio=off stays per-load")
        ck("createGlobe" not in gate_src and "HeatGlobe" in gate_src,
           "the globe is its own component rather than inline in the splash")
        ck(s.get("brandPresent") is True, "the FortyGuard mark sits under the action")
        ck((s.get("brandLabel") or "") == "Powered by",
           "labelled, so the mark cannot read as the author of this product",
           repr(s.get("brandLabel")))
        ck(s.get("logoAlt") == "FortyGuard", "with alt text carrying the same words",
           repr(s.get("logoAlt")))
        ck((s.get("logoNaturalWidth") or 0) > 0,
           "and the image actually LOADED, so the ART path resolves at this depth",
           "naturalWidth=%s src=%s" % (s.get("logoNaturalWidth"), s.get("logoSrc")))
        ck(28 <= (s.get("logoHeight") or 0) <= 44,
           "sized like the banner's copy, and large enough that the thin strokes hold their colour",
           "%s px" % s.get("logoHeight"))
        ck(s.get("noteGone") is True,
           "and the introduction note is gone, at the user's instruction")
        ck(s.get("introAttr") == "gate",
           "body[data-aa-intro] scopes the styles to this stage", str(s.get("introAttr")))
        ck(s.get("configureBlocked") is True,
           "the gate really does cover the page, which is why motion=off exists",
           "point (%s) hits %s" % (s.get("configureHitProbe"), s.get("configureHit")))

        # -------------------------------------------------------------- motion off
        head("3. ?motion=off: NOTHING from intro/ mounts, and the product is reachable")
        d = load(port, "&motion=off", "observe")
        s = last(d)
        ck(s.get("gatePresent") is False, "no gate")
        ck(s.get("hasPersistentMute") is False, "no mute button")
        ck(s.get("introAttr") in (None, "null"), "no body attribute, so intro.css cannot apply",
           str(s.get("introAttr")))
        ck(s.get("configureFound") is True, "Configure this plant is on screen")
        ck(s.get("configureBlocked") is False,
           "and no overlay intercepts the page",
           "point (%s) hits %s" % (s.get("configureHitProbe"), s.get("configureHit")))
        print("      the CTA sits at y=%s in a %spx viewport"
              % (s.get("ctaTop"), s.get("viewportH")))
        ck(not (s.get("media") or {}).get("play"),
           "and no audio was even attempted", str((s.get("media") or {}).get("play")))

        # -------------------------------------------------------------- audio off
        head("4. ?audio=off: the gate still runs, in silence")
        d = load(port, "&audio=off", "enter")
        s = last(d, "after-fade")
        ck(last(d, "before-enter").get("gatePresent") is True, "the gate still appears")
        ck(not (s.get("media") or {}).get("play"),
           "play() was never called on anything", str((s.get("media") or {}).get("play")))
        ck(s.get("hasPersistentMute") is False,
           "and no mute button is offered for sound that cannot happen")

        # -------------------------------------------------------------- enter
        head("5. ENTER: the gate unmounts, sound starts, the toggle appears")
        d = load(port, "", "enter")
        before, after = last(d, "before-enter"), last(d, "after-fade")
        ck(before.get("gatePresent") is True, "gate up before the click")

        # THE SCROLL LOCK. A fixed, full-viewport overlay does NOT stop the document behind it
        # scrolling, and before this was locked a reader who scrolled while the card was up arrived
        # mid-page: measured at scrollY 501 out of a 1,345px document. The lock has to be on the ROOT
        # element, because only the root's overflow propagates to the viewport -- on <body> alone it
        # changed nothing.
        ck(d.get("htmlOverflowGateUp") == "hidden",
           "the root element's overflow is locked while the card owns the screen",
           "html overflow-y: %s (body: %s)"
           % (d.get("htmlOverflowGateUp"), d.get("bodyOverflowGateUp")))
        ck(d.get("docScrollHeight", 0) > 900,
           "and the document behind it really is taller than the viewport, so the lock matters",
           "%s px" % d.get("docScrollHeight"))
        ck(d.get("scrollAfterEnter") == 0,
           "entering reveals the top of the page",
           "scrollY %s" % d.get("scrollAfterEnter"))
        ck(d.get("htmlOverflowAfter") != "hidden",
           "and the lock is RELEASED, so the page scrolls normally again",
           "html overflow-y: %s" % d.get("htmlOverflowAfter"))

        # THE FADE ACTUALLY RENDERS, sampled while it is running rather than after it.
        mid = last(d, "mid-fade")
        ck(mid.get("gatePresent") is True,
           "the card is still mounted 250 ms after the click, so it can fade at all")
        ck(mid.get("gateLeaving") is True,
           "carrying is-leaving", str(mid.get("gateLeaving")))
        # 🔴 THE EXIT IS NO LONGER A CSS TRANSITION, SO THIS ASSERTS THE OWNER AND THE END STATE.
        # It used to be a 700 ms upward sweep declared in intro.css, and this read transitionProperty
        # off the element mid-fade. The user replaced the sweep with a 1.2 s fade and scale timed
        # against a whoosh cue, which has to live on the launch timeline, so CSS no longer declares any
        # transition for the leaving state at all.
        # AND ASSERTING THE ANIMATED VALUE WOULD BE WRONG HERE rather than merely awkward: GSAP does
        # not advance under this harness's virtual clock (05-TRAPS 5b.13, first consequence: "Do not
        # assert an animated VALUE under virtual time. Assert the declaration, the mounted window, and
        # the END STATE"). So: the class carries ONLY the pointer lock, the source shows launch.ts
        # owning the tween, and the gate is gone by the end.
        lsrc = io.open(os.path.join(AA, "app", "src", "intro", "launch.ts"),
                       encoding="utf-8").read()
        icss = io.open(os.path.join(AA, "app", "src", "intro", "intro.css"),
                       encoding="utf-8").read()
        i = icss.index(".aa-gate[role='dialog'].is-leaving {")
        leaving_rule = icss[i:icss.index("}", i)]
        ck("opacity" not in leaving_rule and "transform" not in leaving_rule,
           "the is-leaving class owns ONLY pointer-events, so nothing fights GSAP for the exit",
           " ".join(leaving_rule.split())[:90])
        ck("opacity: 0, scale: 1.06" in lsrc,
           "and launch.ts owns the fade and the scale, in one timeline")
        ck("outS: 1.2" in lsrc, "over 1.2 s, as asked")
        ck(after.get("gatePresent") is False,
           "and the gate is UNMOUNTED once the sequence ends, not left transparent over the page",
           "opacity was %s" % after.get("gateOpacity"))
        ck(after.get("configureBlocked") is False,
           "so the page is reachable again",
           "point (%s) hits %s" % (after.get("configureHitProbe"), after.get("configureHit")))
        ck(after.get("introAttr") == "running", "the intro is marked as running",
           str(after.get("introAttr")))
        ck(after.get("hasPersistentMute") is True, "the persistent mute toggle is in the corner")
        played = (after.get("media") or {}).get("play") or []
        # ALL THREE CUES IN ONE RUN: the voice and its bed at t = 0, the whoosh at the transition.
        # The whoosh is also the check that it fires from a timeline LABEL rather than from the
        # voiceover's ended event, because under virtual time the voice never actually finishes and an
        # ended-chained whoosh would never fire at all.
        ck({"voiceover.mp3", "intro-swell.mp3"}.issubset(set(played)),
           "the voiceover and its bed both played, on the click", str(sorted(set(played))))
        # 🔴 THE WHOOSH IS NOT MEASURED HERE, AND THE REASON IS WORTH STATING RATHER THAN LEAVING AS A
        # SILENT GAP. It fires from a timeline LABEL near the end of the sequence, and GSAP does not
        # advance under this harness's virtual clock, so that label is never reached: what finishes the
        # sequence here is the wall-clock watchdog, which deliberately fires no cues.
        # That is the design working rather than failing. The cue is decoration; the completion is not,
        # and only the completion is guaranteed. `testing/verify_launch.py` runs on a REAL clock and
        # measures the whoosh there, which is the only place the claim can honestly be made.
        ck("playWhoosh" in lsrc,
           "and the whoosh is fired from a timeline label; verify_launch.py measures it for real")
        # 🔴 AND IT STARTED ON THE CLICK, WHICH REVERSES AN EARLIER REQUIREMENT. The brief used to say
        # the narration must play automatically with a first-interaction fallback, and this section
        # asserted both. The current brief says "On click of Initialize Arbiter: ... voiceover.mp3
        # starts", which makes the fallback unnecessary rather than unused: a click IS the gesture
        # browsers require. Section 2 asserts that nothing plays before the click.
        # 🔴 NO CHIME ON THE SPLASH ANY MORE, AND ITS ABSENCE IS NOW THE ASSERTION. The chime was
        # tied to the five stage rows settling, and those moved below the map on 2026-08-29. The cue
        # went with them rather than being deleted, and section 14 measures it in its new place. A
        # chime here would mean something is still sequencing on a screen that no longer has anything
        # to sequence.
        ck(played.count("chime.wav") == 0,
           "and no chime fired on the splash, since the rows it accompanied have moved",
           "%d chimes" % played.count("chime.wav"))
        gsrc = io.open(os.path.join(AA, "app", "src", "intro", "IntroGate.tsx"),
                       encoding="utf-8").read()
        ck("audio.play" not in gsrc and "'pointerdown', kick" not in gsrc,
           "and the gate no longer attempts playback on mount, nor arms an autoplay fallback")
        ck("audio.preload()" in gsrc and "ARM_CAP_MS" in gsrc,
           "what it does instead is preload the three files and arm the CTA when they are in")
        mx = (after.get("media") or {}).get("maxVolume")
        ck(mx is not None and mx <= 0.4 + 1e-9,
           "and volume never exceeded the 0.4 master", "max was %s" % mx)

        # -------------------------------------------------------------- teardown
        head("6. LEAVING THE LANDING STAGE: audio is stopped AND unloaded")
        d = load(port, "", "leave")
        onl, off = last(d, "on-landing"), last(d, "after-leaving")
        ck(onl.get("introAttr") == "running", "running while on the landing stage")
        ck(off.get("stage") == "configure", "the stage really changed", str(off.get("stage")))
        ck(off.get("introAttr") in (None, "null"),
           "the body attribute is gone, so no intro rule applies to the technical screens",
           str(off.get("introAttr")))
        ck(off.get("gatePresent") is False and off.get("hasPersistentMute") is False,
           "and nothing from intro/ is rendered there")
        m = off.get("media") or {}
        ck(len(m.get("pause") or []) >= 2, "both elements were paused",
           str(m.get("pause")))
        # The tail of the load() log is what matters: two loads on elements whose src attribute has
        # already been removed. That pair IS the unload -- pausing alone leaves a decoded buffer and,
        # in some browsers, an open connection.
        ck((m.get("load") or [])[-2:] == ["cleared", "cleared"],
           "and both had their src cleared and reloaded, which is what frees the decoder",
           str(m.get("load")))

        # -------------------------------------------------------------- narrow
        head("7. NARROW (<768px): no gate, no audio, per the brief")
        d = load(port, "", "observe", size=(430, 900))
        s = last(d)
        ck(s.get("gatePresent") is False, "no gate on a phone-width viewport")
        ck(not (s.get("media") or {}).get("play"), "and no audio",
           str((s.get("media") or {}).get("play")))
        ck(s.get("configureBlocked") is not True, "the product is reachable")
        # 🔴 THE ONE THING THE BRIEF SAYS TO KEEP ON MOBILE. This section used to assert only the
        # negatives -- no gate, no audio, product reachable -- and passed for four steps while the
        # hero reveal was not running on a phone at all: the entrance was gated on `flags.gate`, and
        # gateEnabled() is false under 768px. A review found it; nothing here would have.
        ck((s.get("heroMs") or 0) > 0,
           "but the hero text reveal DOES run, which is the brief's mobile requirement",
           "timeline %s ms" % s.get("heroMs"))

        # -------------------------------------------------------------- reduced motion
        head("8. prefers-reduced-motion: no gate, no audio, page still finished")
        d = load(port, "", "observe", extra=("--force-prefers-reduced-motion",))
        s = last(d)
        ck(s.get("gatePresent") is False, "no gate")
        ck(not (s.get("media") or {}).get("play"),
           "audio defaults to off, as the brief asks",
           str((s.get("media") or {}).get("play")))
        ck(s.get("configureFound") is True,
           "and the page is complete rather than mid-animation")

        # ---------------------------------------------------------- the hero
        head("9. THE HERO ENTRANCE, and the guarantee that it always finishes")
        d = load(port, "", "enter")
        pre, post = last(d, "before-enter"), last(d, "settled")

        ck((pre.get("heroMs") or 0) == 0 or pre.get("heroMs") is None,
           "no timeline exists before Enter is pressed", str(pre.get("heroMs")))
        ck((post.get("heroMs") or 0) > 0,
           "one is built on the click, and publishes its own duration",
           "%s ms" % post.get("heroMs"))
        # THE BRIEF'S 1.6 s, READ FROM GSAP. `enter` runs with sound on, so this is the stretched
        # map; the silent one is measured separately below.
        ck((post.get("heroMs") or 0) <= 6000,
           "the audio-synced timeline stays inside the voiceover",
           "%s ms" % post.get("heroMs"))

        d2 = load(port, "&audio=off", "enter")
        silent = last(d2, "settled")
        ms = silent.get("heroMs") or 0
        ck(0 < ms <= 1600,
           "and on its own, with no audio, it is under the 1.6 s the brief allows",
           "%s ms" % ms)

        # 🔴 THE HERO ENTRANCE IS ALWAYS THE SILENT MAP NOW, AND THAT IS WHAT IS ASSERTED.
        # These two checks used to require the audio-synced beat map to be LONGER than the silent one
        # and to land inside the voiceover, because the narration played underneath this entrance. The
        # voiceover moved to the launch sequence on 2026-08-29, so by the time the entrance runs the
        # narration has finished and there is nothing left to sync to. The two runs are now identical
        # BY DESIGN, and the call site says so rather than leaving it to coincidence.
        audio_ms = post.get("heroMs") or 0
        ck(abs(audio_ms - ms) < 60,
           "the hero entrance runs the silent map whether or not sound is on, because the narration "
           "now finishes before it starts",
           "%s ms with audio vs %s ms silent" % (audio_ms, ms))
        lay_src = io.open(os.path.join(AA, "app", "src", "intro", "IntroLayer.tsx"),
                          encoding="utf-8").read()
        ck("playHeroEntrance(false, 'full')" in lay_src,
           "and IntroLayer asks for it explicitly at the call site")
        tl_src = io.open(os.path.join(AA, "app", "src", "intro", "timeline.ts"),
                         encoding="utf-8").read()
        ck("VOICE.nameEndsS" in tl_src and "VOICE.poweredStartsS" in tl_src,
           "every audio beat is derived from the measured file, not typed as a constant")
        ck("durationS: 4.676" in tl_src,
           "and the duration recorded there is the one measured from the shipped file")

        # 🔴 THE PAGE ENDS FINISHED WHATEVER HAPPENS TO THE TICKER. Every from-state here is written
        # by GSAP, opacity: 0 included -- correct, because a stylesheet would leave the page blank
        # whenever the animation is off. The cost is that visibility depends on a timeline
        # completing, and MEASURED: under Chrome's virtual-time headless mode the timeline never
        # advances at all (rAF fires, nothing throws, GSAP writes the from-states, progress stays 0).
        # A watchdog jumps it to the end. This harness is therefore not a limitation to work around
        # but the exact adversarial condition worth asserting against.
        for name, snap in (("with sound", post), ("silent", silent)):
            hero = snap.get("hero") or {}
            # 🔴 THE FIVE TARGETS ARE NAMED HERE RATHER THAN DISCOVERED FROM THE RESULT, so a selector
            # that stops matching FAILS instead of removing its own checks. That is the whole lesson of
            # the 208-to-204 drop: iterating over what the probe happened to find means a broken
            # selector reports success by not reporting at all.
            for key in ('cta', 'eyebrow', 'headline', 'prose', 'status'):
                v = hero.get(key)
                ok = bool(v) and v.get("found") is True
                ck(ok, "%s  %s was found at all" % (name, key),
                   "" if ok else ("selector %s matched nothing"
                                  % (v or {}).get("sel", "?") if v else "absent"))
                if not v or v.get("found") is not True:
                    continue
                ck(v["op"] == "1", "%s  %s ends fully opaque" % (name, key),
                   "opacity %s" % v["op"])
                ck(v["tr"] in ("none", "matrix(1, 0, 0, 1, 0, 0)"),
                   "%s  %s ends untransformed" % (name, key), v["tr"])
            b = snap.get("brandStyle") or {}
            ck(b.get("op") == "1", "%s  the FortyGuard mark ends visible" % name,
               "opacity %s" % b.get("op"))

        ck(post.get("splitWrappers") == 0 and post.get("maskDivs") == 0,
           "SplitText's wrappers are reverted, so the shipped DOM is what a reader gets",
           "%s line wrappers, %s masks" % (post.get("splitWrappers"), post.get("maskDivs")))
        ck("text-ink-2" in (post.get("headlineHTML") or ""),
           "and the headline's original markup is restored, span and all",
           repr((post.get("headlineHTML") or "")[:60]))

        # MOTION OFF AND REDUCED MOTION MUST LEAVE THE HERO ALONE ENTIRELY.
        for label, query, extra in (("?motion=off", "&motion=off", ()),
                                    ("reduced motion", "", ("--force-prefers-reduced-motion",))):
            d3 = load(port, query, "observe", extra=extra)
            s3 = last(d3)
            ck(s3.get("heroMs") is None,
               "%s: no timeline is built at all" % label, str(s3.get("heroMs")))
            ck(s3.get("splitWrappers") == 0,
               "%s: the headline is never split" % label)
            h3 = s3.get("hero") or {}
            worst = [k for k, v in h3.items() if v["op"] != "1"]
            ck(not worst, "%s: every hero element is already final" % label,
               "not opaque: %s" % worst if worst else "%d checked" % len(h3))

        # ---------------------------------------------------------- the loop
        head("10. THE AGENT LOOP: five real stages, a closed cycle, a travelling pulse")
        # `d` and `silent` are the two `enter` runs from section 9, sampled at 6.2 s -- past both
        # entrances and well into the ambient loops.
        r = post.get("ring") or {}
        ck(r.get("present") is True, "the diagram is rendered")
        ck(r.get("displayed") is True, "and displayed at desktop width")
        keys = [n["key"] for n in (r.get("nodes") or [])]
        ck(keys == ["perceive", "bound", "decide", "act", "score"],
           "five stages, in pipeline order", str(keys))
        labels = [n["label"] for n in (r.get("nodes") or [])]
        ck(labels == ["PERCEIVE", "BOUND", "DECIDE", "ACT", "SCORE"],
           "named from AgentConsole's own stage list", str(labels))
        ck(r.get("returnLabel") == "RECALIBRATE",
           "and RECALIBRATE labels the return leg, which is what closes the loop",
           str(r.get("returnLabel")))
        ck(r.get("hasArrow") is True,
           "with a direction mark, so the return leg is not ambiguous")
        ck("five stages" in (r.get("srText") or ""),
           "a text alternative states the loop for a screen reader",
           repr(r.get("srText")))

        # EVERY NODE ARRIVES. The entrance scales them in; a node left at opacity 0 or scaled down
        # would be a stage a reader never learns about.
        for n in r.get("nodes") or []:
            ck(n["groupOpacity"] == "1", "  %s arrives" % n["key"],
               "opacity %s" % n["groupOpacity"])
        ck(all((n.get("note") or "") for n in (r.get("nodes") or [])),
           "each stage carries a description of what it DOES, not a value",
           "; ".join((n.get("note") or "?") for n in (r.get("nodes") or []))[:70])

        # 🔴 THE ANIMATED LABEL NEVER DROPS BELOW ITS CONTRAST FLOOR. The pulse response used to
        # fade these to 0.45, which composites to 2.38:1 in dark and 2.11:1 in light against a
        # 4.5:1 requirement -- illegible for most of every cycle. The floor is 0.85, measured; the
        # visible response moved to the halo, which carries no text.
        for n in r.get("nodes") or []:
            op = n.get("noteOpacity")
            ck(op is not None and op >= 0.84,
               "  %s's label stays above its measured contrast floor" % n["key"],
               "opacity %s" % op)

        # 🔴 NOTHING IN A NODE IS EVER DISPLACED FROM THE REST OF IT.
        # The halo and the disc are concentric by construction, so any gap between their centres is a
        # transform origin being wrong. It was: 8.62px at worst, which put a ghost circle a hundred
        # pixels from its node during the pulse and was spotted in a capture, not by a check. CSS
        # `transform-origin` is inert here (GSAP writes `transform-origin: 0px 0px` inline) and
        # `transformOrigin: 'center'` in the tween did not fix it either, because the group's bounding
        # box includes the label text beneath the disc. `svgOrigin`, in user units, did.
        da = load(port, "&audio=off", "align")
        al = (da or {}).get("align") or {}
        ck((al.get("samples") or 0) > 300,
           "the alignment probe sampled the whole entrance and several pulse cycles",
           "%s samples" % al.get("samples"))
        ck(al.get("worst") is not None and al.get("worst") <= 0.6,
           "and no node's halo ever left its own disc",
           "worst %s px at %s" % (al.get("worst"), al.get("worstNode")))
        for k, v in sorted((al.get("perNode") or {}).items()):
            ck(v <= 0.6, "  %s stays concentric" % k, "%s px" % v)

        ck(r.get("running") == "running",
           "the ambient loops are running", str(r.get("running")))
        ck(r.get("pulseVisibility") == "visible", "the pulse is on screen",
           str(r.get("pulseVisibility")))
        ck((r.get("pulseTransform") or "none") != "none",
           "and has been moved along the path, so it is travelling rather than parked",
           str(r.get("pulseTransform"))[:46])

        # MOTION OFF: no diagram at all, because it belongs to the intro layer.
        d4 = load(port, "&motion=off", "observe")
        s4 = last(d4)
        ck((s4.get("ring") or None) is None,
           "?motion=off: the diagram is not rendered at all")

        # REDUCED MOTION: the diagram IS there and complete, and the pulse is not.
        d5 = load(port, "", "observe", extra=("--force-prefers-reduced-motion",))
        s5 = last(d5)
        r5 = s5.get("ring") or {}
        ck(r5.get("present") is True,
           "reduced motion: the diagram is still rendered, because it is the explainer")
        ck(len(r5.get("nodes") or []) == 5, "with all five stages",
           "%d nodes" % len(r5.get("nodes") or []))
        ck(all(n["groupOpacity"] == "1" for n in (r5.get("nodes") or [])),
           "all of them visible, so it reads as finished rather than mid-animation")
        ck(r5.get("pulseVisibility") == "hidden",
           "and the pulse is absent", str(r5.get("pulseVisibility")))
        ck(r5.get("running") is None, "with no ambient loops started",
           str(r5.get("running")))

        # NARROW: the pulse must not run. The brief: "Mobile (<768px): ... disable pipeline pulse".
        d6 = load(port, "", "observe", size=(430, 900))
        s6 = last(d6)
        r6 = s6.get("ring") or {}
        ck(r6.get("running") is None,
           "narrow: no pulse and no float, per the brief", str(r6.get("running")))
        ck(r6.get("displayed") is False,
           "and the 1180-unit diagram is not squeezed into a phone viewport",
           "display none" if r6.get("displayed") is False else "STILL DISPLAYED")

        # ---------------------------------------------------------- the field
        head("11. THE HEAT FIELD: behind everything, slow, and nowhere but the landing stage")
        t = post.get("thermal") or {}
        ck(bool(t), "the field is rendered on the landing stage")
        ck(t.get("parentIsBody") is True,
           "as a direct child of body, which is the only place it can paint below the content",
           "parentIsBody=%s" % t.get("parentIsBody"))
        ck(t.get("position") == "fixed" and t.get("zIndex") == "0",
           "fixed at z-index 0", "%s / %s" % (t.get("position"), t.get("zIndex")))
        ck(t.get("appZIndex") == "1",
           "with #app raised above it, so the order is explicit rather than incidental",
           "#app z-index %s" % t.get("appZIndex"))
        op = t.get("opacity")
        ck(op is not None and 0.12 <= op <= 0.18,
           "opacity inside the brief's 0.12 to 0.18", str(op))
        ck(t.get("pointerEvents") == "none",
           "and it cannot intercept a click", str(t.get("pointerEvents")))
        # 🔴 BEHIND ALL CONTENT, measured at a pixel rather than argued from z-index.
        ck(t.get("coversContent") is False,
           "the point over the headline hits the headline, not the field",
           "field intercepts = %s" % t.get("coversContent"))

        for layer in ("a", "b"):
            L = t.get(layer) or {}
            ck((L.get("name") or "none") != "none",
               "  layer %s is animating" % layer, str(L.get("name")))
            dur = L.get("dur") or ""
            try:
                secs = float(dur.rstrip("s"))
            except ValueError:
                secs = -1.0
            # 🔴 SLOWER THAN ASKED IS THE SAFE DIRECTION. The brief says 45-60s and "if motion is
            # perceptible at a glance, it's too fast", and `alternate` makes a full there-and-back
            # twice the declared duration -- so 50s and 58s are 100s and 116s round trip.
            ck(45.0 <= secs <= 60.0,
               "  layer %s cycles inside 45 to 60 s" % layer, dur)
            ck(L.get("dir") == "alternate" and L.get("iter") == "infinite",
               "  layer %s alternates forever, so it never snaps back" % layer,
               "%s / %s" % (L.get("dir"), L.get("iter")))
            ck(L.get("moved") is True,
               "  layer %s carries a transform, which is the only thing animated" % layer)

        # THE ONE THAT MATTERS: gone the moment the reader leaves the landing stage.
        dl = load(port, "", "leave")
        onl2, off2 = last(dl, "on-landing"), last(dl, "after-leaving")
        ck(bool(onl2.get("thermal")), "present while on the landing stage")
        ck(off2.get("stage") == "configure", "the stage really changed",
           str(off2.get("stage")))
        ck(off2.get("thermal") is None,
           "and REMOVED on the configure screen, which must stay completely static",
           "still present" if off2.get("thermal") else "gone")

        # MOTION OFF: no field at all.
        ck((s4.get("thermal") or None) is None,
           "?motion=off: no field is rendered")

        # REDUCED MOTION AND NARROW: the field stays, the motion stops.
        for label, snap in (("reduced motion", s5), ("narrow", s6)):
            tt = snap.get("thermal") or {}
            ck(bool(tt), "%s: the field is still there, so the page looks finished" % label)
            for layer in ("a", "b"):
                L = tt.get(layer) or {}
                ck((L.get("name") or "none") == "none",
                   "%s: layer %s is not animating" % (label, layer), str(L.get("name")))

        # AND THE BANNER MARK IS UNCHANGED BY ANY OF THIS.
        # 🔴 FULL OPACITY IN BOTH PALETTES, and the check is per-theme because the bug was too.
        # cinematic.css carried the first brief's watermark treatment -- `opacity: 0.34`, and `0.46`
        # for the light theme. masthead.css superseded it and says so in as many words, but
        # `.aa-banner img` is (0,1,1) and `:root[data-theme='light'] .aa-banner img` is (0,3,1), so
        # the stale rule won in ONE palette. The mark rendered vivid in dark and pale in light, same
        # asset, same page, and the user photographed it. The dead rules are deleted; this is what
        # would catch them coming back.
        bl = post.get("bannerLogo") or {}
        ck(bl.get("opacity") == "1",
           "the banner's FortyGuard mark is at full opacity", str(bl.get("opacity")))
        ck((bl.get("filter") or "none") != "none",
           "and still carries its per-theme correction", str(bl.get("filter"))[:52])
        ck(32 <= (bl.get("h") or 0) <= 46,
           "and is large enough to read as an attribution rather than a watermark",
           "%s px" % bl.get("h"))

        # ---------------------------------------------------------- the handoff
        head("12. THE SCROLL HANDOFF: the pitch ends, and it ends BOTH WAYS")
        # A second server with a long hold, so this one scenario can run on a real clock.
        srv2, port2 = serve(hold="12")
        try:
            dh = load(port2, "&audio=off", "handoff", size=(1440, 820), realtime=True)
        finally:
            srv2.terminate()
        rows = (dh or {}).get("handoff") or []
        ck(len(rows) >= 8, "the handoff probe completed its down-and-up sweep",
           "%d samples" % len(rows))
        if rows:
            for r2 in rows:
                print("      y=%-4s fade=%-6s field=%-7s ring=%s"
                      % (r2["y"], round(r2["fade"], 3) if r2["fade"] is not None else None,
                         round(r2["fieldOpacity"], 4) if r2["fieldOpacity"] is not None else None,
                         round(r2["ringOpacity"], 3) if r2["ringOpacity"] is not None else None))
            first = rows[0]
            ck(first["fade"] is not None and first["fade"] > 0.98,
               "at the top the field is at full strength", str(first.get("fade")))
            ck(first["ringOpacity"] is not None and first["ringOpacity"] > 0.98,
               "and the diagram is fully visible", str(first.get("ringOpacity")))

            down = [r2 for r2 in rows[: rows.index(max(rows, key=lambda x: x["y"])) + 1]]
            ck(all(down[i]["fade"] >= down[i + 1]["fade"] - 1e-6 for i in range(len(down) - 1)),
               "the fade only ever decreases on the way down, never bounces",
               " -> ".join(str(round(x["fade"], 3)) for x in down))
            bottom = max(rows, key=lambda x: x["y"])
            ck(bottom["fade"] is not None and bottom["fade"] < 0.02,
               "by the time the technical content is in view the field is gone",
               "fade %s at y=%s" % (round(bottom["fade"], 4), bottom["y"]))
            ck(bottom["ringOpacity"] is not None and bottom["ringOpacity"] < 0.02,
               "and so is the diagram", str(round(bottom["ringOpacity"], 4)))

            # 🔴 THE REVERSE LEG. This is the assertion the original bug would have failed.
            back = rows[-1]
            ck(back["scrollY"] == 0, "the probe really returned to the top",
               "scrollY %s" % back["scrollY"])
            ck(back["fade"] is not None and back["fade"] > 0.98,
               "and scrolling back restores the field, rather than leaving it faded for good",
               "fade %s" % round(back["fade"], 3))
            ck(back["ringOpacity"] is not None and back["ringOpacity"] > 0.98,
               "and restores the diagram", str(round(back["ringOpacity"], 3)))
            # Symmetry: the same scroll position must give the same value on the way up.
            pairs = {}
            for r2 in rows:
                pairs.setdefault(r2["y"], []).append(r2["fade"])
            asym = {y: v for y, v in pairs.items() if len(v) > 1 and abs(v[0] - v[-1]) > 0.02}
            ck(not asym,
               "and the same scroll position gives the same fade in both directions",
               "asymmetric at %s" % asym if asym else "%d positions compared twice"
               % sum(1 for v in pairs.values() if len(v) > 1))

        # ---------------------------------------------------------- contrast
        head("13. EVERY LINE ON THE GATE CLEARS 4.5:1, IN BOTH PALETTES")
        # 4.5:1 rather than the 3:1 used for the popovers: this is prose on a full screen, so WCAG AA
        # for body text is the right bar. Three real failures were found by measuring rather than
        # looking -- the note at 4.44:1 dark and 3.71:1 light (an `opacity: 0.72`), and the eyebrow at
        # 4.27:1 in light only (--fg-bright is a different value per theme).
        for theme in ("dark", "light"):
            d = load(port, "", "observe", page="_intro_%s.html" % theme)
            s = last(d)
            rows = s.get("contrast") or []
            ck(s.get("theme") == theme, "%s theme loaded" % theme, str(s.get("theme")))
            ck(len(rows) >= 5, "all five splash text elements measured in %s" % theme,
               "%d measured" % len(rows))
            worst = min(rows, key=lambda r: r["ratio"]) if rows else None
            for r in sorted(rows, key=lambda r: r["ratio"]):
                detail = ("UNPARSEABLE colour %s" % r["unparsed"]) if r.get("unparsed") else (
                    "%.2f:1 at %s w%s" % (r["ratio"], r["size"], r["weight"]))
                ck(r["ratio"] >= 4.5, "%s  %s" % (theme, r["sel"]), detail)
            if worst:
                print("      worst in %s: %s at %.2f:1" % (theme, worst["sel"], worst["ratio"]))
            # THE MARK IS CORRECTED PER THEME, and this is the check that would have caught the
            # washed-out banner logo the user reported: those filters live on `.aa-banner img`, and
            # the gate's mark is not inside the banner, so it needed its own rule in each palette.
            f = s.get("logoFilter")
            ck(bool(f) and f != "none",
               "%s  the FortyGuard mark carries its palette correction" % theme, str(f))
        # ---------------------------------------------------------- no WebGL
        head("13b. WITH NO WEBGL AT ALL, THE PRODUCT STILL RENDERS")
        # 🔴 THIS SECTION EXISTS BECAUSE THE PAGE WENT BLANK AND NOTHING HERE NOTICED.
        # `new THREE.WebGLRenderer()` THROWS when it cannot get a context rather than returning null.
        # Thrown from inside HeatGlobe's effect, with no boundary above it, React unmounted the whole
        # tree: measured, `#root` went from one child to zero. The agent, the map, the panels and the
        # report all disappeared because a background animation could not start.
        # ⚠ EVERY OTHER SCENARIO IN THIS FILE PASSES `--enable-unsafe-swiftshader --use-gl=angle`,
        # because MapLibre needs it. A harness that always supplies the thing under test cannot see its
        # absence, which is 05-TRAPS 5b.7 in another costume. So this one takes it away.
        d = load(port, "", "observe", extra=("--disable-webgl", "--disable-3d-apis"))
        s = last(d)
        ck(bool(d) and not d.get("err"), "the probe ran with WebGL disabled",
           (d or {}).get("err") or "")
        ck(s.get("gatePresent") is True,
           "the splash still renders, so a throw in the globe did not take the tree down")
        ck(s.get("hasEnter") is True and (s.get("enterLabel") or "") == "Initialize Arbiter",
           "its call to action is there and readable", repr(s.get("enterLabel")))
        ck(bool(s.get("gateTitle")), "and the wordmark", repr(s.get("gateTitle")))
        # The globe's canvas element still exists; what is absent is anything drawn into it. That is
        # the wanted degradation: the scenery goes, the page stays.
        g = s.get("globeCanvas") or {}
        ck(bool(g), "the canvas element is still in the DOM, simply not drawn into")
        ck(g.get("hasGL") in (False, None),
           "and it genuinely has no GL context, so this scenario is testing what it claims",
           str(g.get("hasGL")))

        d2 = load(port, "&motion=off", "observe", extra=("--disable-webgl", "--disable-3d-apis"))
        s2 = last(d2)
        ck(s2.get("configureFound") is True,
           "and with the intro off as well, the product itself is reachable")

        src_b = io.open(os.path.join(AA, "app", "src", "components", "IntroBoundary.tsx"),
                        encoding="utf-8").read()
        ck("getDerivedStateFromError" in src_b and "componentDidCatch" in src_b,
           "an error boundary wraps the motion layer, as the belt to that brace")
        appsrc = io.open(os.path.join(AA, "app", "src", "App.tsx"), encoding="utf-8").read()
        ck("<IntroBoundary>" in appsrc and "<IntroLayer />" in appsrc,
           "and App.tsx actually wraps IntroLayer in it rather than only importing it")

        # ---------------------------------------------------------- the stage rows are gone
        head("14. THE FIVE STAGE ROWS ARE GONE FROM THE PAGE")
        # 🔴 TWO INSTRUCTIONS, AND THEY ARE ONLY COMPATIBLE ONE WAY.
        # Moving the rows out of the hero came with "do not delete the underlying component or data
        # wiring". Removing them came later the same day: "remove this", with a screenshot of the
        # section below the map. Gone from the page, kept on disk is the only reading that honours
        # both, so BOTH halves are asserted: nothing rendered, and the files still present.
        # ⚠ THIS SECTION IS SMALLER THAN THE TWO IT REPLACES, and deliberately so. There is less
        # product to check: the previous 14 walked five rows, their labels, notes, icons, timestamps,
        # their below-the-fold position and their scroll-triggered arrival, and 15 measured their
        # contrast in both palettes. None of that exists to measure now, and padding the count with
        # checks of an absent feature would be the opposite of what these files are for.
        for query, label in (("", "with the intro running"),
                             ("&motion=off", "with ?motion=off")):
            d = load(port, query, "observe")
            s = last(d)
            ck(s.get("stageRowsAnywhere") == 0,
               "no .aa-stagerow, .aa-stagerows or .aa-splash-widget anywhere %s" % label,
               "%s found" % s.get("stageRowsAnywhere"))

        src = io.open(os.path.join(AA, "app", "src", "App.tsx"), encoding="utf-8").read()
        ck("<StageRows />" not in src, "App.tsx does not render the section")
        ck("from './components/StageRows'" not in src,
           "and does not import it, so it is tree-shaken out of the bundle rather than shipped dead")
        for f in ("StageRows.tsx", "stagerows.css"):
            ck(os.path.isfile(os.path.join(AA, "app", "src", "components", f)),
               "%s is still on disk, per the instruction not to delete the wiring" % f)

    finally:
        srv.terminate()
        for n in ("_intro.html", "_intro_dark.html", "_intro_light.html"):
            try:
                os.remove(os.path.join(DIST, n))
            except OSError:
                pass

    bad = [c for c in CHECKS if not c[0]]
    print()
    print("=" * 78)
    print("   %d checks, %d failed" % (len(CHECKS), len(bad)))
    if bad:
        for _, label, detail in bad:
            print("   FAILED: %s   %s" % (label, detail))
    else:
        print("   VERDICT: the gate opens, unmounts, and hands the product back; motion=off leaves")
        print("            no trace of it; audio obeys its master, its mute and its teardown.")
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
