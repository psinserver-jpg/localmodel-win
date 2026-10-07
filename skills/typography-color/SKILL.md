---
name: typography-color
description: Typography and color craft for web UI: modular fluid type scale, font pairing with Korean stacks, line length and leading, palettes built from one brand hue (HSL/OKLCH), WCAG contrast numbers, gradients, dark palettes and 8 ready palettes. Use for fonts, text hierarchy, color schemes and contrast fixes.
triggers: [typography, font, fonts, font size, font pairing, typeface, type scale, line height, letter spacing, text hierarchy, readability, color palette, color scheme, color theme, brand color, primary color, contrast, wcag, accessible colors, gradient, dark mode colors, oklch, hsl, palette, 타이포그래피, 폰트, 글꼴, 글자 크기, 글씨체, 행간, 자간, 가독성, 색상, 색상표, 컬러, 컬러 팔레트, 배색, 색 조합, 브랜드 컬러, 대비, 그라데이션, 다크모드 색, 프리텐다드, 노토 산스]
priority: 47
---
# Typography and Color

## Type rules (decide, then apply everywhere)
1. Max 2 families. One is fine. Weights: 400, 500/600, 700 only.
2. Korean sites: `font-family: "Pretendard Variable", Pretendard, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;` plus `word-break: keep-all; overflow-wrap: anywhere;` and `<html lang="ko">`.
   - Pretendard: `<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">`
   - Serif/editorial Korean: `"Noto Serif KR"` (Google Fonts) for headings only.
3. Scale ratio 1.25 (UI) or 1.333 (marketing). Body 16px min (17-18px for articles). Fluid headings with `clamp()`:
   `--fs-0: 1rem; --fs-1: clamp(1.1rem, 1.05rem + .25vw, 1.25rem); --fs-2: clamp(1.25rem, 1.1rem + .75vw, 1.563rem); --fs-3: clamp(1.563rem, 1.3rem + 1.3vw, 2.25rem); --fs-4: clamp(2rem, 1.5rem + 2.5vw, 3.25rem); --fs-5: clamp(2.5rem, 1.6rem + 4.5vw, 4.75rem)`.
4. Leading: body 1.6 (Korean 1.7-1.8), headings 1.1-1.25, UI labels 1.2-1.3. Big display text gets tighter leading (1.05).
5. Tracking: Latin headings `-0.02em`; Korean headings `-0.01em`..0; ALL-CAPS labels `+0.08em` (never uppercase Korean); never negative tracking on body.
6. Measure: `max-width: 65ch` (Korean about 38-45 characters per line). `text-wrap: balance` headings, `text-wrap: pretty` paragraphs.
7. Hierarchy = size + weight + color. Three text colors only: `--text` (primary), `--text-muted` (secondary, >= 4.5:1), accent. No opacity tricks below .7.
8. Numbers: `font-variant-numeric: tabular-nums` in tables/prices/timers; `lining-nums` for UI; Korean currency "38,000원" with `toLocaleString('ko-KR')`.
9. Links: underline body links, color >= 4.5:1 vs surrounding text or underline mandatory.

## Color rules
1. Palette = neutral scale (9-11 steps) + 1 primary + optional 1 accent + semantic (success/warning/danger/info). Max 3 hues. 60/30/10 usage.
2. Build from ONE hue in HSL: primary `hsl(H 85% 50%)`; hover = L-6%; soft tint `hsl(H 90% 96%)`; border `hsl(H 20% 88%)`. Neutrals: take the same hue at saturation 6-12% (tinted greys feel cohesive, not dead grey).
3. Prefer `oklch(L C H)` for even lightness (L .55-.62 for buttons, C .15-.20) with HSL/hex fallback written first.
4. WCAG 2.2 AA numbers: body text >= 4.5:1; large text (>= 24px or >= 18.66px bold) >= 3:1; UI components, icons, focus ring, input borders >= 3:1; AAA body 7:1. Contrast ratio = (L1+.05)/(L2+.05) with relative luminance (function in reference/palettes-contrast.md).
5. Known facts: `#767676` is the lightest grey text on white (4.54:1); `#9ca3af` on white 2.5:1 fails; white on `#3b82f6` 3.7:1 fails -> `#2563eb` 5.2:1; white on `#10b981` fails -> `#047857`; amber `#f59e0b` needs dark text `#1f2937`.
6. Never convey meaning by color alone (add icon/text). Red/green pairs: also vary lightness.
7. Dark mode: bg `#0f1115`-`#18181b` (never `#000`), text `#e6e8ec` (never `#fff`), surfaces get LIGHTER with elevation, desaturate brand by 10-15% and raise lightness until >= 4.5:1; dark text on bright buttons.
8. Gradients that look good: same hue family +/- 30-40deg, similar lightness, `linear-gradient(135deg, ...)`, subtle (low contrast) behind text; or mesh via 2-3 `radial-gradient` blobs at 15-30% opacity on a solid bg. Avoid rainbow, pure-saturated purple-to-pink, and gradient text on small type. Interpolate smoothly: `linear-gradient(in oklch, ...)` with plain fallback line before it.
9. Keep text on images readable: overlay `linear-gradient(to top, rgb(0 0 0 / .65), transparent 60%)`.

## Compact example (one brand hue 222, calm SaaS)
```css
:root {
  --h: 222;
  --bg: hsl(var(--h) 20% 98%);
  --surface: #fff;
  --border: hsl(var(--h) 14% 88%);
  --text: hsl(var(--h) 25% 12%);
  --text-muted: hsl(var(--h) 10% 40%);
  --primary: hsl(var(--h) 83% 47%);
  --primary-hover: hsl(var(--h) 83% 40%);
  --primary-soft: hsl(var(--h) 90% 96%);
  --hero-bg: linear-gradient(135deg, hsl(var(--h) 90% 96%), hsl(calc(var(--h) + 35) 90% 94%));
  --font: "Pretendard Variable", Pretendard, "Noto Sans KR", system-ui, sans-serif;
}
body { font: 400 1rem/1.7 var(--font); color: var(--text); background: var(--bg); word-break: keep-all; }
h1 { font-size: clamp(2.25rem, 1.6rem + 3.6vw, 4rem); line-height: 1.12; letter-spacing: -.02em; text-wrap: balance; }
.eyebrow { font-size: .8125rem; font-weight: 700; letter-spacing: .08em; color: var(--primary); }
p { max-width: 65ch; color: var(--text-muted); text-wrap: pretty; }
.price { font-variant-numeric: tabular-nums; font-weight: 700; }
```
```js
const lum = (hex) => {
  const c = hex.replace('#', '').match(/../g).map((h) => parseInt(h, 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a, b) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};
console.log(contrast('#2563eb', '#ffffff').toFixed(2)); // 5.17
```

## Pitfalls
- Pure `#000` on `#fff` for big areas is harsh; use `#111`-`#1a1a1a` on `#fafafa`.
- Fonts via `@import` block rendering; use `<link>` + `font-display: swap`.
- Hero h1 at 2.25rem on a 360px phone with `keep-all`: long Korean words overflow; keep `overflow-wrap: anywhere`.
- Too many greys: pick the 9-step neutral scale and stick to it.
- Do not set `line-height` in px; unitless.
- Palettes (8 moods, hex) and the full contrast/palette generator: reference/palettes-contrast.md. Type scale generator and pairings: reference/type-scale-pairing.md.
