---
name: logo-examples
description: Six complete copy-ready SVG logos in different styles - wordmark, monogram, geometric symbol, combination mark, circular emblem badge, gradient overlap mark - with adaptation notes.
triggers: [logo example, logo examples, svg logo, wordmark, monogram, emblem, badge logo, geometric logo, gradient logo, combination mark, logo template, 로고 예제, 로고 예시, 워드마크, 모노그램, 엠블럼, 뱃지 로고, 기하학 로고, 그라데이션 로고]
---
# Six SVG logos (adapt names, colors; keep construction)

Fonts: `Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', system-ui, sans-serif`. Prefix ids per logo.

## 1. Wordmark (tech/SaaS, name "nexa")
```html
<svg viewBox="0 0 180 56" width="180" height="56" role="img" aria-label="nexa" xmlns="http://www.w3.org/2000/svg">
  <text x="4" y="42" font-family="Inter, Pretendard, system-ui, sans-serif" font-size="44" font-weight="800" letter-spacing="-2" fill="#111827">nexa<tspan fill="#4f46e5">.</tspan></text>
</svg>
```
One weight, tight tracking, one colored dot as the only accent.

## 2. Monogram (law/finance, "한")
```html
<svg viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="한솔 법률 로고" xmlns="http://www.w3.org/2000/svg">
  <rect width="64" height="64" rx="12" fill="#0b2a5b"/>
  <rect x="5" y="5" width="54" height="54" rx="8" fill="none" stroke="#c8a24a" stroke-width="2"/>
  <text x="32" y="45" text-anchor="middle" font-family="'Noto Serif KR', 'Nanum Myeongjo', Georgia, serif" font-size="36" font-weight="700" fill="#c8a24a">한</text>
</svg>
```
Serif Hangul + inner gold keyline = trust and tradition. Works as avatar and favicon (drop the keyline at 16px).

## 3. Geometric symbol (eco brand, leaf from two circles)
```html
<svg viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="새싹 심볼" xmlns="http://www.w3.org/2000/svg">
  <path d="M32 6C50 6 58 20 58 32c0 14-10 26-26 26S6 46 6 32C6 20 14 6 32 6z" fill="#14532d"/>
  <path d="M32 54V26" stroke="#e7dcc3" stroke-width="4" stroke-linecap="round" fill="none"/>
  <path d="M32 34c0-8-5-12-12-12 0 8 4 12 12 12zM32 28c0-7 4-11 12-11 0 7-4 11-12 11z" fill="#e7dcc3"/>
</svg>
```
Construction: a square with 2 rounded corners (leaf silhouette), a stem and two leaves; 3 shapes, 2 colors.

## 4. Combination mark (fitness app "Pulse")
```html
<svg viewBox="0 0 220 64" width="220" height="64" role="img" aria-label="Pulse" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="30" fill="#e11d48"/>
  <path d="M10 34h11l5-12 8 22 6-14h14" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="76" y="43" font-family="Inter, Pretendard, system-ui, sans-serif" font-size="32" font-weight="800" letter-spacing="-1" fill="#111827">Pulse</text>
</svg>
```
Heartbeat line inside a circle; symbol height 64 = clear lockup height; text cap-height aligned near the symbol's centerline.

## 5. Circular emblem badge (bakery "달빛제과")
```html
<svg viewBox="0 0 120 120" width="120" height="120" role="img" aria-label="달빛제과 엠블럼" xmlns="http://www.w3.org/2000/svg">
  <defs><path id="emb-arc" d="M18 60a42 42 0 0 1 84 0"/></defs>
  <circle cx="60" cy="60" r="56" fill="#fff4e0" stroke="#7c4a2d" stroke-width="3"/>
  <circle cx="60" cy="60" r="48" fill="none" stroke="#7c4a2d" stroke-width="1.5" stroke-dasharray="2 4"/>
  <text font-family="Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif" font-size="15" font-weight="800" fill="#7c4a2d" letter-spacing="3">
    <textPath href="#emb-arc" startOffset="50%" text-anchor="middle">달빛제과</textPath></text>
  <path d="M60 40a18 18 0 1 0 14 29 14 14 0 1 1-14-29z" fill="#e4572e"/>
  <text x="60" y="100" text-anchor="middle" font-family="Georgia, serif" font-size="9" letter-spacing="2" fill="#7c4a2d">SINCE 2014</text>
</svg>
```
Crescent moon from two arcs. Text on a path follows the top arc.

## 6. Gradient overlap mark (creative studio "Orbit")
```html
<svg viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="Orbit" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="orb-a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c3aed"/><stop offset="1" stop-color="#06b6d4"/></linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="#0b1020"/>
  <circle cx="26" cy="32" r="16" fill="url(#orb-a)"/>
  <circle cx="40" cy="32" r="16" fill="#f43f5e" fill-opacity=".75" style="mix-blend-mode:screen"/>
</svg>
```
Two overlapping circles = simplest memorable symbol. Blend mode is ignored by some renderers; the 75% alpha still reads fine.

## Showing logos on a page (light/dark)
```html
<style>
:root { --logo-ink: #111827; --logo-bg: #fff; }
@media (prefers-color-scheme: dark) { :root { --logo-ink: #f5f7fb; --logo-bg: #0b1020; } }
.logo-box { background: var(--logo-bg); padding: 24px; border-radius: 16px; display: inline-grid; place-items: center; }
.logo-box svg text { fill: var(--logo-ink); }
</style>
```
Use `fill="currentColor"` + `color: var(--logo-ink)` on the svg wrapper to make a single-color logo follow the theme.
