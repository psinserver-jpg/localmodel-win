---
name: svg-recipes
description: Copy-ready SVG - 12 stroke icons, wave and curve dividers, morphing blob, gradients, glow filter, line-draw and CSS/SMIL animation, accessible markup.
triggers: [svg icon, icon set, icons, wave, wave divider, section divider, blob, morph, gradient, svg animation, smil, line draw, stroke dash, svg filter, glow, sprite, symbol, 아이콘 세트, 파도 구분선, 블롭, 곡선, svg 애니메이션, 선 그리기, 스프라이트]
---
# SVG recipes

## Icon set (24px grid, stroke style, use as inline SVG or a `<symbol>` sprite)
```html
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-home" viewBox="0 0 24 24"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></symbol>
  <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></symbol>
  <symbol id="i-user" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/></symbol>
  <symbol id="i-heart" viewBox="0 0 24 24"><path d="M12 21s-8-5.2-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 5.8-8 11-8 11z"/></symbol>
  <symbol id="i-bell" viewBox="0 0 24 24"><path d="M6 17V11a6 6 0 0 1 12 0v6l2 2H4z"/><path d="M10 21h4"/></symbol>
  <symbol id="i-gear" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></symbol>
  <symbol id="i-check" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5"/></symbol>
  <symbol id="i-close" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></symbol>
  <symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></symbol>
  <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
  <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>
  <symbol id="i-chart" viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></symbol>
</svg>
<style>
.ico { width: 1.5rem; height: 1.5rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
</style>
<button class="btn" aria-label="검색"><svg class="ico" aria-hidden="true"><use href="#i-search"/></svg></button>
```
Icon-only buttons need `aria-label` (Korean). Icon next to text: `aria-hidden` on the svg. Do not use emoji as UI icons.

## Wave dividers (put at the bottom of a colored section; fill = next section color)
```html
<div style="background:#4f46e5;line-height:0">
  <svg viewBox="0 0 1440 120" preserveAspectRatio="none" style="display:block;width:100%;height:80px" aria-hidden="true">
    <path d="M0 64 C240 120 480 0 720 48 C960 96 1200 16 1440 64 V120 H0 Z" fill="#f8fafc"/>
  </svg>
</div>
```
Other dividers: slant `M0 0 L1440 120 H0 Z`; curve `M0 0 Q720 160 1440 0 V120 H0 Z`; layered waves: stack 2-3 paths with `fill-opacity` .3 / .5 / 1. `preserveAspectRatio="none"` stretches the wave; strokes would distort, so waves are fills only.

## Animated wave (CSS, transform only)
```html
<style>
.waves { position: relative; height: 120px; overflow: hidden; background: #4f46e5; }
.waves svg { position: absolute; left: 0; bottom: 0; width: 200%; height: 100%; animation: slide 12s linear infinite; }
.waves svg:nth-child(2) { animation-duration: 18s; opacity: .5; }
@keyframes slide { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .waves svg { animation: none; } }
</style>
<div class="waves">
  <svg viewBox="0 0 2880 120" preserveAspectRatio="none"><path d="M0 60 C360 120 720 0 1080 60 C1440 120 1800 0 2160 60 C2520 120 2880 0 2880 60 V120 H0Z" fill="#f8fafc"/></svg>
</div>
```
The path repeats every 1440 units over a 2880 viewBox, so shifting -50% loops seamlessly.

## Animated gradient blob (SMIL path morph)
```html
<svg viewBox="0 0 400 400" style="width:min(80vw,360px);height:auto" role="img" aria-label="움직이는 그라데이션 도형">
  <defs>
    <linearGradient id="blobGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7c3aed"/><stop offset="1" stop-color="#06b6d4"/>
    </linearGradient>
  </defs>
  <path fill="url(#blobGrad)" d="M312 120C352 180 340 270 280 320C220 370 130 350 90 290C50 230 70 140 130 90C190 40 272 60 312 120Z">
    <animate attributeName="d" dur="9s" repeatCount="indefinite" calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1;.4 0 .6 1" keyTimes="0;.33;.66;1"
      values="M312 120C352 180 340 270 280 320C220 370 130 350 90 290C50 230 70 140 130 90C190 40 272 60 312 120Z;
              M330 150C370 210 320 290 260 330C200 370 110 340 80 270C50 200 90 120 150 80C210 40 290 90 330 150Z;
              M300 100C350 160 350 250 290 310C230 370 120 360 80 300C40 240 60 150 120 100C180 50 250 40 300 100Z;
              M312 120C352 180 340 270 280 320C220 370 130 350 90 290C50 230 70 140 130 90C190 40 272 60 312 120Z"/>
  </path>
</svg>
```
All keyframe paths must have the SAME command sequence (here M + 5 C + Z) for morphing to work. For reduced-motion users remove the animation with JS: `if (matchMedia('(prefers-reduced-motion: reduce)').matches) document.querySelectorAll('animate').forEach(a => a.remove());`.

## Line drawing + glow
```html
<svg viewBox="0 0 200 80" style="width:100%;max-width:420px">
  <defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
  <path id="ln" d="M10 60 C40 10 70 70 100 30 S160 10 190 40" fill="none" stroke="#22d3ee" stroke-width="3" stroke-linecap="round" filter="url(#glow)"/>
</svg>
<style>
#ln { stroke-dasharray: var(--len); stroke-dashoffset: var(--len); animation: draw 2s ease forwards; }
@keyframes draw { to { stroke-dashoffset: 0; } }
</style>
<script>
const ln = document.getElementById('ln');
ln.style.setProperty('--len', ln.getTotalLength());
</script>
```

## CSS pivot animation (spin / pulse / bob)
```css
.spin { transform-box: fill-box; transform-origin: center; animation: spin 6s linear infinite; }
.pulse { transform-box: fill-box; transform-origin: center; animation: pulse 2s ease-in-out infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 50% { transform: scale(1.12); } }
```

## Simple illustration kit
Build scenes from basic shapes on a 400x300 viewBox: sky = `<rect>` with vertical gradient; sun = `<circle>` with radial gradient; hills = `<path>` with `C` curves in 2-3 tints of ONE hue (back lighter); clouds = 3 overlapping `<circle>` + `<rect>` white at .9 opacity; flat style, no outlines, max 5 colors, shadows as same-hue darker shapes.
