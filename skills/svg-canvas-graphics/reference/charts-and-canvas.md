---
name: charts-and-canvas
description: Hand-made SVG bar plus line chart from data, canvas drawing helpers, animated gradient blob on canvas, generative art (flow field, spirograph), pointer interaction.
triggers: [bar chart, line chart, svg chart, hand-made chart, chart without library, canvas helper, generative art, flow field, spirograph, canvas animation, gradient blob canvas, mouse interaction canvas, pointer, 막대 차트, 선 차트, 차트 직접, 캔버스 도우미, 제너러티브, 생성 예술, 마우스 반응]
---
# Hand-made chart and canvas recipes

## Bar + line chart in plain SVG (revenue bars, growth line)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>월별 매출 차트</title>
<style>
:root { --bar:#4f46e5; --line:#f59e0b; --grid:#e5e7eb; --ink:#111827; --muted:#6b7280; }
body { margin: 0; padding: 1rem; background: #f8fafc; color: var(--ink); font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
figure { margin: 0 auto; max-width: 44rem; background: #fff; border-radius: 16px; padding: 1.25rem; box-shadow: 0 1px 3px rgb(0 0 0 / .1); }
figcaption { font-weight: 700; margin-bottom: .75rem; }
svg { display: block; width: 100%; height: auto; }
svg text { font-size: 12px; fill: var(--muted); }
.legend { display: flex; gap: 1rem; font-size: .875rem; color: var(--muted); margin-top: .5rem; }
.legend i { display: inline-block; width: .75rem; height: .75rem; border-radius: 3px; margin-right: .35rem; }
</style></head>
<body>
<figure>
  <figcaption>2025년 월별 매출과 증가율</figcaption>
  <svg id="chart" viewBox="0 0 640 320" role="img" aria-label="월별 매출 막대와 증가율 선 차트"></svg>
  <div class="legend"><span><i style="background:var(--bar)"></i>매출(백만 원)</span><span><i style="background:var(--line)"></i>증가율(%)</span></div>
</figure>
<script>
const months = ['1월','2월','3월','4월','5월','6월'];
const sales = [120, 150, 135, 190, 210, 260];
const growth = [4, 25, -10, 41, 11, 24];
const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('chart');
const m = { l: 44, r: 44, t: 16, b: 32 };
const W = 640, H = 320, iw = W - m.l - m.r, ih = H - m.t - m.b;
const maxS = Math.ceil(Math.max(...sales) / 50) * 50;
const gMin = -20, gMax = 60;
function el(name, attrs, text) {
  const e = document.createElementNS(NS, name);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  svg.appendChild(e);
  return e;
}
const yS = (v) => m.t + ih - (v / maxS) * ih;
const yG = (v) => m.t + ih - ((v - gMin) / (gMax - gMin)) * ih;
for (let i = 0; i <= 5; i++) {
  const v = (maxS / 5) * i, y = yS(v);
  el('line', { x1: m.l, x2: W - m.r, y1: y, y2: y, stroke: '#e5e7eb' });
  el('text', { x: m.l - 8, y: y + 4, 'text-anchor': 'end' }, v);
}
const step = iw / months.length, bw = step * 0.55;
const pts = [];
months.forEach((name, i) => {
  const x = m.l + step * i + (step - bw) / 2;
  const y = yS(sales[i]);
  const r = el('rect', { x, y, width: bw, height: m.t + ih - y, rx: 4, fill: '#4f46e5' });
  const t = document.createElementNS(NS, 'title');
  t.textContent = name + ' 매출 ' + sales[i] + '백만 원';
  r.appendChild(t);
  el('text', { x: x + bw / 2, y: H - 10, 'text-anchor': 'middle' }, name);
  pts.push([x + bw / 2, yG(growth[i])]);
});
el('polyline', { points: pts.map((p) => p.join(',')).join(' '), fill: 'none', stroke: '#f59e0b', 'stroke-width': 3, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' });
pts.forEach((p, i) => {
  el('circle', { cx: p[0], cy: p[1], r: 4.5, fill: '#fff', stroke: '#f59e0b', 'stroke-width': 2.5 });
  el('text', { x: p[0], y: p[1] - 10, 'text-anchor': 'middle', style: 'fill:#92400e;font-weight:700;paint-order:stroke;stroke:#fff;stroke-width:3px' }, growth[i] + '%');
});
for (const v of [-20, 0, 20, 40, 60]) el('text', { x: W - m.r + 8, y: yG(v) + 4 }, v + '%');
</script>
</body></html>
```
Pattern: margins object, two scale functions, helper `el()`, axis, bars, line, labels. For a time series with many points use `<path d="M x y L ...">` and an area fill `fill="url(#g)"` closed down to the baseline.

## Canvas helpers (paste once)
```js
function setupCanvas(cv) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const rand = (a, b) => a + Math.random() * (b - a);
function pointerPos(cv, e) {
  const r = cv.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}
function loop(fn) {
  let last = performance.now(), id = 0;
  const tick = (t) => { const dt = Math.min((t - last) / 1000, 0.05); last = t; fn(dt, t / 1000); id = requestAnimationFrame(tick); };
  id = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(id);
}
```

## Animated gradient blobs on canvas (mouse-reactive)
```html
<canvas id="blobs" style="width:100%;height:60vh;display:block;background:#0b1020"></canvas>
<script>
const cv = document.getElementById('blobs');
let { ctx, w, h } = setupCanvas(cv);
const colors = ['#7c3aed', '#06b6d4', '#f43f5e'];
const blobs = colors.map((c, i) => ({ c, a: i * 2.1, sp: 0.25 + i * 0.12, r: 0.32 }));
const mouse = { x: w / 2, y: h / 2 };
cv.addEventListener('pointermove', (e) => { const p = pointerPos(cv, e); mouse.x = p.x; mouse.y = p.y; });
new ResizeObserver(() => { ({ ctx, w, h } = setupCanvas(cv)); }).observe(cv);
loop((dt, t) => {
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#0b1020';
  ctx.fillRect(0, 0, w, h);
  ctx.globalCompositeOperation = 'lighter';
  blobs.forEach((b, i) => {
    b.a += b.sp * dt;
    const R = Math.min(w, h) * b.r;
    const x = w / 2 + Math.cos(b.a + i) * w * 0.28 + (mouse.x - w / 2) * 0.15 * (i + 1) / 3;
    const y = h / 2 + Math.sin(b.a * 1.3 + i) * h * 0.25 + (mouse.y - h / 2) * 0.15 * (i + 1) / 3;
    const g = ctx.createRadialGradient(x, y, 0, x, y, R);
    g.addColorStop(0, b.c + 'cc');
    g.addColorStop(1, b.c + '00');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, R, 0, Math.PI * 2); ctx.fill();
  });
});
</script>
```
Needs the helpers above in the same file. Hex + `cc`/`00` gives 8-digit hex alpha. Radial gradients are cheap; no CSS blur needed.

## Generative art: spirograph
```html
<canvas id="spiro" style="width:min(90vw,480px);aspect-ratio:1;background:#0f172a;border-radius:16px"></canvas>
<script>
const sc = document.getElementById('spiro');
const dpr = Math.min(window.devicePixelRatio || 1, 2);
sc.width = sc.clientWidth * dpr; sc.height = sc.clientHeight * dpr;
const g = sc.getContext('2d');
g.setTransform(dpr, 0, 0, dpr, 0, 0);
const S = sc.clientWidth, R = S * 0.36, r = R * 0.37, d = r * 0.9;
let a = 0;
function draw() {
  for (let k = 0; k < 40; k++) {
    const x = (R - r) * Math.cos(a) + d * Math.cos(((R - r) / r) * a);
    const y = (R - r) * Math.sin(a) - d * Math.sin(((R - r) / r) * a);
    g.fillStyle = 'hsl(' + ((a * 20) % 360).toFixed(0) + ' 90% 65%)';
    g.fillRect(S / 2 + x, S / 2 + y, 1.6, 1.6);
    a += 0.02;
  }
  if (a < 400) requestAnimationFrame(draw);
}
draw();
</script>
```

## Generative art: flow field trails
```js
// fragment: uses setupCanvas and loop from the helpers above
const cv2 = document.querySelector('canvas');
let { ctx, w, h } = setupCanvas(cv2);
const N = 600;
const ps = Array.from({ length: N }, () => ({ x: Math.random() * w, y: Math.random() * h }));
ctx.fillStyle = '#0b1020'; ctx.fillRect(0, 0, w, h);
loop((dt, t) => {
  ctx.fillStyle = 'rgba(11,16,32,0.06)';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(125,211,252,0.8)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (const p of ps) {
    const ang = Math.sin(p.x * 0.004 + t * 0.2) * Math.PI + Math.cos(p.y * 0.004) * Math.PI;
    const nx = p.x + Math.cos(ang) * 60 * dt * 3, ny = p.y + Math.sin(ang) * 60 * dt * 3;
    ctx.moveTo(p.x, p.y); ctx.lineTo(nx, ny);
    p.x = nx; p.y = ny;
    if (p.x < 0 || p.x > w || p.y < 0 || p.y > h) { p.x = Math.random() * w; p.y = Math.random() * h; }
  }
  ctx.stroke();
});
```
