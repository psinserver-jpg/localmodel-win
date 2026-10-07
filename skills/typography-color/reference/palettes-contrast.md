---
name: palettes-contrast
description: Eight ready color palettes (hex, light plus dark) for different moods, a contrast-ratio and palette-generator JS toolkit, neutral scales, semantic colors and gradient recipes.
triggers: [palette, color palette, color scheme, hex colors, brand colors, mood colors, contrast ratio, wcag, color generator, neutral scale, semantic colors, gradient, oklch, hsl, 팔레트, 색상표, 컬러 팔레트, 배색, 색 조합, 브랜드 컬러, 대비, 그라데이션, 분위기]
---
# Palettes and contrast

Each palette: `bg / text / muted / primary (on white text) / accent`, then a dark variant. All text pairs were measured: body text and muted >= 4.5:1, primary vs white >= 4.9:1, dark primary vs dark bg >= 6.9:1.

| Mood (use for) | bg | text | muted | primary | accent | dark bg | dark primary |
|---|---|---|---|---|---|---|---|
| 1 Calm SaaS blue (B2B, finance, tools) | #f8fafc | #0f172a | #475569 | #2563eb | #0ea5e9 | #0f1115 | #7aa7ff |
| 2 Fresh mint (health, eco, wellness) | #f4fbf7 | #0f2a22 | #4b6358 | #047857 | #f59e0b | #0d1512 | #4ade9b |
| 3 Warm sunset (food, community, kids) | #fff8f3 | #2b1a12 | #6b5548 | #c2410c | #eab308 | #17110d | #fb923c |
| 4 Royal violet (creative, AI, music) | #faf8ff | #1e1633 | #5d5675 | #6d28d9 | #ec4899 | #120f1c | #a78bfa |
| 5 Rose bloom (beauty, fashion, wedding) | #fff7fa | #2a1220 | #6e5262 | #be185d | #f59e0b | #1a0f15 | #f472b6 |
| 6 Ocean teal (travel, medical, calm) | #f3fafb | #0c2a31 | #4a6870 | #0e7490 | #f97316 | #0b1719 | #22d3ee |
| 7 Mono ink (editorial, portfolio, luxury) | #fafafa | #111111 | #595959 | #111827 | #dc2626 | #0a0a0a | #e5e5e5 |
| 8 Gold luxe (premium, hospitality, law) | #faf7f0 | #1c1917 | #6b6358 | #a16207 | #1e3a5f | #14110b | #e0b04a |

Accent colors are for decoration/large elements; if used as text or button fill check contrast (amber/yellow/cyan accents need dark text on them).

### Palette as CSS (example: Fresh mint, copy and swap hex from the table)
```css
:root {
  --bg: #f4fbf7; --surface: #ffffff; --border: #d6e7de;
  --text: #0f2a22; --text-muted: #4b6358;
  --primary: #047857; --primary-hover: #065f46; --on-primary: #ffffff;
  --accent: #f59e0b; --on-accent: #1f2937;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0d1512; --surface: #14201b; --border: #24362e;
    --text: #e6f2ec; --text-muted: #9bb3a8;
    --primary: #4ade9b; --primary-hover: #7ceab8; --on-primary: #06281a;
  }
}
```

## Neutral scale (tinted, 11 steps) from a hue
```css
:root {
  --h: 220;
  --n-50:  hsl(var(--h) 20% 98%);  --n-100: hsl(var(--h) 16% 95%);  --n-200: hsl(var(--h) 14% 90%);
  --n-300: hsl(var(--h) 12% 82%);  --n-400: hsl(var(--h) 10% 64%);  --n-500: hsl(var(--h) 9% 46%);
  --n-600: hsl(var(--h) 10% 36%);  --n-700: hsl(var(--h) 12% 26%);  --n-800: hsl(var(--h) 15% 16%);
  --n-900: hsl(var(--h) 20% 10%);  --n-950: hsl(var(--h) 25% 6%);
}
```
Text on white: use 600+ (n-500 is about 4.8:1 at this hue, n-400 fails). On n-900: use n-200 or lighter.

## Semantic colors (AA with white text on the fill, or the fill as text on white)
- success `#15803d` (5.0:1) soft `#e4f6ea`; warning `#b45309` (5.0:1) soft `#fdf1dc`; danger `#c62828` (5.6:1) soft `#fdeaea`; info `#0369a1` (5.9:1) soft `#e2f2fb`.
- Dark UI: success `#5fd38a`, warning `#f5b94a`, danger `#ff8a80`, info `#6cc4f0` on `#0f1115`.

## Contrast + palette toolkit (JS)
```js
export function luminance(hex) {
  const [r, g, b] = hex.replace('#', '').match(/../g).map((h) => {
    const v = parseInt(h, 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(fg, bg) {
  const a = luminance(fg);
  const b = luminance(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

export function grade(ratio, large = false) {
  if (ratio >= 7) return 'AAA';
  if (ratio >= (large ? 3 : 4.5)) return 'AA';
  return 'fail';
}

export function hslToHex(h, s, l) {
  s /= 100; l /= 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return '#' + [f(0), f(8), f(4)].map((x) => Math.round(x * 255).toString(16).padStart(2, '0')).join('');
}

// 10-step scale from a single hue (50 lightest ... 900 darkest)
export function scaleFromHue(h, sat = 80) {
  const lights = [97, 93, 85, 74, 62, 50, 42, 34, 26, 18];
  return Object.fromEntries(lights.map((l, i) => [(i === 0 ? 50 : i * 100), hslToHex(h, sat, l)]));
}

// darken a color until it reaches the target contrast on a background
export function ensureContrast(hue, sat, bg, target = 4.5) {
  for (let l = 60; l >= 5; l -= 1) {
    const c = hslToHex(hue, sat, l);
    if (contrastRatio(c, bg) >= target) return c;
  }
  return '#000000';
}

console.log(contrastRatio('#767676', '#ffffff').toFixed(2), grade(contrastRatio('#2563eb', '#ffffff')));
```
In a single HTML file drop `export` and use plain functions in the inline script.

## OKLCH version (modern browsers) with fallback
```css
:root {
  --primary: #2563eb;                       /* fallback first */
  --primary: oklch(0.55 0.2 262);
  --primary-soft: oklch(0.96 0.03 262);
  --primary-hover: oklch(0.48 0.2 262);
}
.hero { background: #eef2ff; background: linear-gradient(in oklch 135deg, oklch(0.96 0.04 262), oklch(0.94 0.05 300)); }
.btn:hover { background: color-mix(in oklab, var(--primary) 88%, black); }
```
Keep the same L for same-importance tokens; change only H to get a harmonious second hue (+/- 30-60).

## Gradient recipes
```css
.grad-calm   { background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%); }
.grad-sunset { background: linear-gradient(135deg, #fff1e6 0%, #ffe4ec 100%); }
.grad-brand  { background: linear-gradient(135deg, #1d4ed8 0%, #0e7490 100%); color: #fff; }
.grad-mesh   { background:
    radial-gradient(40rem 30rem at 10% 0%, rgb(37 99 235 / .18), transparent 60%),
    radial-gradient(36rem 28rem at 90% 10%, rgb(14 165 233 / .16), transparent 60%),
    var(--bg); }
.grad-text   { background: linear-gradient(90deg, #2563eb, #0e7490); -webkit-background-clip: text; background-clip: text; color: transparent; }
```
White text on `.grad-brand`: both ends >= 5:1, safe. Gradient text only on big headings (>= 32px).
