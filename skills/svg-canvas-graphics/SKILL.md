---
name: svg-canvas-graphics
description: Inline SVG illustration, icons, wave dividers, hand-made charts and animation, plus Canvas 2D (DPR-correct resize, rAF loop, particles, generative art). Use for SVG, canvas, icons, illustrations, particle backgrounds and animated graphics.
triggers: [svg, canvas, icon, icons, illustration, vector, path, viewbox, wave divider, blob, particles, particle background, generative art, requestanimationframe, animation, animated background, chart, bar chart, line chart, stroke, gradient fill, svg filter, smil, 캔버스, 아이콘, 일러스트, 벡터, 파티클, 파도, 블롭, 애니메이션, 차트, 그래프, 배경 효과, 도형]
priority: 45
---
# SVG and Canvas graphics

Single HTML file, no libraries. SVG for icons, illustration, charts (crisp, stylable, accessible). Canvas for many moving things (>300 objects), pixels, particles.

## SVG rules
1. Always `viewBox` and NO fixed width/height on inline SVG; size it with CSS (`width: 100%; height: auto;` or `1.5rem` for icons).
2. Icons: `viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"`. Color follows CSS `color`. Size 20/24px; touch target stays 44px on the button, not the svg.
3. Decorative svg: `aria-hidden="true"`. Meaningful svg: `role="img"` + `<title>` + `aria-labelledby`.
4. Every `id` (gradient/filter/clipPath) must be unique in the page; two inline SVGs with the same `id="g"` break each other.
5. Draw on a grid of whole numbers; use `<path d>` with `M L H V C Q A Z`; round coordinates to 1 decimal.
6. Gradients: `<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">` (objectBoundingBox units, 0-1) then `fill="url(#g)"`.
7. Animate with CSS (`transform-box: fill-box; transform-origin: center;` so rotate/scale pivot on the shape) or SMIL `<animate>`/`<animateTransform>`. Line draw: `stroke-dasharray: L; stroke-dashoffset: L;` animate offset to 0 (get L from `path.getTotalLength()`).
8. Blur/glow: `<filter id="glow"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`.
9. Charts: compute coordinates in JS from data, `y = H - v/max*H`; add axis, gridlines `#e5e7eb`, labels `font-size: 12px`, value labels, `<title>` tooltips.

## Canvas rules
1. DPR-correct: `canvas.width = cssW * dpr; ctx.setTransform(dpr,0,0,dpr,0,0)`; resize on `ResizeObserver`, never in the draw loop.
2. One `requestAnimationFrame` loop; compute `dt = (t - last) / 1000` capped at `0.05` s, move by `speed * dt` (frame-rate independent).
3. Pause on `document.hidden`; honor `prefers-reduced-motion` (draw one static frame).
4. Clear with `clearRect` (or a translucent `fillRect` for trails). Batch: one `beginPath()` for many same-colored shapes, one `fill()`.
5. Background canvas: `position: fixed; inset: 0; z-index: -1; pointer-events: none;`.
6. Never allocate objects per frame; keep arrays of plain objects created once.

## Example: particle background (copy whole)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>파티클 배경</title>
<style>
body { margin: 0; min-height: 100svh; display: grid; place-items: center; background: #0b1020; color: #fff;
  font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; word-break: keep-all; }
#bg { position: fixed; inset: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }
h1 { font-size: clamp(2rem, 6vw, 3.5rem); text-align: center; margin: 0; }
</style></head>
<body>
<canvas id="bg"></canvas>
<h1>별빛이 흐르는 밤</h1>
<script>
const cv = document.getElementById('bg');
const ctx = cv.getContext('2d');
const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
let W = 0, H = 0, parts = [], last = 0, raf = 0;
function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  W = cv.clientWidth; H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const n = Math.round(Math.min(120, (W * H) / 14000));
  parts = Array.from({ length: n }, () => ({
    x: Math.random() * W, y: Math.random() * H,
    vx: (Math.random() - 0.5) * 30, vy: (Math.random() - 0.5) * 30,
    r: 1 + Math.random() * 1.5,
  }));
}
function frame(t) {
  const dt = Math.min((t - last) / 1000, 0.05); last = t;
  ctx.clearRect(0, 0, W, H);
  for (const p of parts) {
    p.x += p.vx * dt; p.y += p.vy * dt;
    if (p.x < 0 || p.x > W) p.vx *= -1;
    if (p.y < 0 || p.y > H) p.vy *= -1;
  }
  ctx.lineWidth = 1;
  for (let i = 0; i < parts.length; i++) {
    for (let j = i + 1; j < parts.length; j++) {
      const a = parts[i], b = parts[j];
      const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (d < 110) {
        ctx.strokeStyle = 'rgba(147,197,253,' + (0.35 * (1 - d / 110)).toFixed(3) + ')';
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
    }
  }
  ctx.fillStyle = '#e0f2fe';
  ctx.beginPath();
  for (const p of parts) { ctx.moveTo(p.x + p.r, p.y); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); }
  ctx.fill();
  if (!still && !document.hidden) raf = requestAnimationFrame(frame);
}
function start() { cancelAnimationFrame(raf); last = performance.now(); raf = requestAnimationFrame(frame); }
new ResizeObserver(() => { resize(); start(); }).observe(cv);
document.addEventListener('visibilitychange', () => { if (!document.hidden && !still) start(); });
</script>
</body></html>
```

## Pitfalls
- Canvas looks blurry on phones = forgot DPR. Canvas text/fonts: wait for `document.fonts.ready` before drawing.
- Resizing canvas via CSS only stretches pixels; set the width/height attributes.
- Keep ONE rAF id and `cancelAnimationFrame` it before restarting, or loops double up and speed doubles.
- `stroke-width` scales with viewBox; add `vector-effect="non-scaling-stroke"` for constant lines.
- More: reference/svg-recipes.md (icons, wave divider, blob, animations), reference/charts-and-canvas.md (bar+line chart, generative art, helpers).
