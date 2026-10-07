---
name: css-3d-and-motion
description: CSS 3D transforms - perspective, card flip, tilt-on-hover with JS, layered parallax, scroll progress bar and scroll-driven animation, with full single-file demos.
triggers: [3d, perspective, preserve-3d, flip card, card flip, tilt, tilt card, parallax, scroll-driven, scroll animation, scroll progress, rotate, 3d card, 3d css, 카드 뒤집기, 틸트, 패럴랙스, 스크롤 애니메이션, 스크롤 진행, 3d 카드, 회전]
---
# 3D transforms and motion (CSS + a little JS)

Rules: `perspective` on the PARENT (600-1200px; smaller = stronger distortion). The rotating element needs `transform-style: preserve-3d`. Faces need `backface-visibility: hidden` (plus the `-webkit-` prefix). Never put `overflow: hidden`, `filter` or `opacity < 1` on a preserve-3d element.

## Flip card (hover on desktop, tap/focus on touch)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>카드 뒤집기</title>
<style>
body { margin: 0; min-height: 100svh; display: grid; place-items: center; background: #0f172a;
  font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; word-break: keep-all; }
.flip { width: 16rem; height: 20rem; perspective: 1000px; border: 0; background: none; padding: 0; cursor: pointer; }
.inner { display: block; position: relative; width: 100%; height: 100%; transform-style: preserve-3d; transition: transform .7s cubic-bezier(.2,.8,.2,1); }
.flip:hover .inner, .flip:focus-visible .inner, .flip.on .inner { transform: rotateY(180deg); }
.face { position: absolute; inset: 0; display: grid; place-content: center; gap: .5rem; padding: 1.5rem; text-align: center;
  border-radius: 20px; color: #fff; -webkit-backface-visibility: hidden; backface-visibility: hidden; }
.front { background: linear-gradient(135deg, #7c3aed, #2563eb); font-size: 1.5rem; font-weight: 800; }
.back { background: #1e293b; transform: rotateY(180deg); line-height: 1.7; }
@media (prefers-reduced-motion: reduce) { .inner { transition: none; } }
</style></head>
<body>
<button class="flip" aria-label="카드 뒤집기"><span class="inner"><span class="face front">오늘의 메뉴</span><span class="face back"><b>된장찌개 정식</b><span>8,500원 · 11:30 오픈</span></span></span></button>
<script>
const card = document.querySelector('.flip');
card.addEventListener('click', () => card.classList.toggle('on'));
</script>
</body></html>
```

## Tilt on hover (pointer position, plus moving glare)
```html
<style>
.stage { perspective: 800px; display: inline-block; }
.tilt { --rx: 0deg; --ry: 0deg; --gx: 50%; --gy: 50%; width: 18rem; aspect-ratio: 4/5; border-radius: 20px; position: relative;
  background: linear-gradient(135deg, #0ea5e9, #6366f1); transform: rotateX(var(--rx)) rotateY(var(--ry));
  transition: transform .15s ease-out; will-change: transform; }
.tilt::after { content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  background: radial-gradient(circle at var(--gx) var(--gy), rgb(255 255 255 / .35), transparent 55%); }
</style>
<div class="stage"><div class="tilt" id="tilt"></div></div>
<script>
const el = document.getElementById('tilt');
const MAX = 12;
el.addEventListener('pointermove', (e) => {
  const r = el.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width;
  const y = (e.clientY - r.top) / r.height;
  el.style.setProperty('--ry', ((x - 0.5) * 2 * MAX).toFixed(2) + 'deg');
  el.style.setProperty('--rx', ((0.5 - y) * 2 * MAX).toFixed(2) + 'deg');
  el.style.setProperty('--gx', (x * 100).toFixed(1) + '%');
  el.style.setProperty('--gy', (y * 100).toFixed(1) + '%');
});
el.addEventListener('pointerleave', () => {
  el.style.setProperty('--rx', '0deg');
  el.style.setProperty('--ry', '0deg');
});
</script>
```
Disable on touch: wrap the listener in `if (matchMedia('(hover: hover)').matches)`.

## CSS 3D cube (no JS)
```css
.scene { width: 10rem; height: 10rem; perspective: 900px; }
.cube { position: relative; width: 100%; height: 100%; transform-style: preserve-3d; animation: spin 12s linear infinite; }
.cube div { position: absolute; inset: 0; border: 2px solid rgb(255 255 255 / .6); background: rgb(99 102 241 / .35); }
.cube .f { transform: translateZ(5rem); } .cube .b { transform: rotateY(180deg) translateZ(5rem); }
.cube .r { transform: rotateY(90deg) translateZ(5rem); } .cube .l { transform: rotateY(-90deg) translateZ(5rem); }
.cube .t { transform: rotateX(90deg) translateZ(5rem); } .cube .d { transform: rotateX(-90deg) translateZ(5rem); }
@keyframes spin { to { transform: rotateX(360deg) rotateY(360deg); } }
```
translateZ = half of the cube size.

## Parallax (cheap, JS-free)
```css
.px { height: 100svh; overflow-y: auto; overflow-x: hidden; perspective: 1px; perspective-origin: center top; }
.px .layer { position: absolute; inset: 0; transform-origin: center top; }
.px .back { transform: translateZ(-1px) scale(2); }
.px .mid { transform: translateZ(-.5px) scale(1.5); }
.px .content { position: relative; transform: translateZ(0); }
```
Alternative with JS: on scroll set `--y` on `:root` via requestAnimationFrame and use `transform: translateY(calc(var(--y) * -0.3px))`. Disable both under reduced-motion.

## Scroll progress bar + scroll reveal (native, with fallback)
```css
.bar { position: fixed; left: 0; top: 0; height: 4px; width: 100%; background: #7c3aed; transform: scaleX(0); transform-origin: 0 50%; }
@supports (animation-timeline: scroll()) {
  .bar { animation: grow linear both; animation-timeline: scroll(root block); }
  .rv { animation: rv linear both; animation-timeline: view(); animation-range: entry 0% cover 35%; }
}
@keyframes grow { to { transform: scaleX(1); } }
@keyframes rv { from { opacity: 0; transform: translateY(32px); } to { opacity: 1; transform: none; } }
```
JS fallback for reveal (all browsers): `new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && e.target.classList.add('in')), { threshold: .15 })`, with `.rv:not(.in)` hidden only when `html.js` is set.

## Sticky stacked cards
```css
.stack section { position: sticky; top: calc(4rem + var(--i) * 1rem); }
```
Set `style="--i:0"`, `--i:1`... on each section; every card slides over the previous one.
