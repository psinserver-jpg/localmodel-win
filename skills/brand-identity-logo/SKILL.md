---
name: brand-identity-logo
description: Logo and brand identity craft with inline SVG - wordmark, monogram, symbol and combination marks, geometric construction, color and type by industry, favicon and app-icon sizes, light/dark variants, mini brand guide. Use for logos, brand identity, favicons and avatars.
triggers: [logo, brand, branding, brand identity, brand guide, wordmark, monogram, emblem, symbol, favicon, app icon, avatar, profile picture, color palette, brand colors, mark, logotype, style guide, 로고, 브랜드, 브랜딩, 브랜드 가이드, 심볼, 모노그램, 워드마크, 파비콘, 앱 아이콘, 프로필 이미지, 아바타, 색상 팔레트, 브랜드 컬러, 상호, 로고 만들기]
priority: 47
---
# Brand identity and logo (SVG)

Deliver a logo as ONE inline `<svg>` that works at 16px and at 512px, in light and dark, plus a short brand guide.

## Hard rules
1. Pick the type: wordmark (name only, best for long/unique names), monogram (1-2 letters, best for avatars/favicons), symbol (icon only, needs a famous brand), combination (symbol + wordmark, safest default). Always also provide a square icon version for favicon/avatar.
2. Construct on a grid: `viewBox="0 0 64 64"` for icons (`0 0 240 64` for horizontal lockups). Use whole numbers, circles, squares, 45/90 degree angles, and ONE stroke width (e.g. 4). Max 2-3 shapes for the symbol idea. If it needs more than 5 shapes it is an illustration, not a logo.
3. Max 2 brand colors + neutral. Flat fills, no gradients required (gradient allowed on one shape). Must work in one color: test with `fill="currentColor"`.
4. Balance: optical center slightly above geometric center; keep 1x clear space (height of the mark's "x") on every side; align symbol with the wordmark cap height or x-height; symbol-to-text gap = 0.5 x symbol height.
5. Type: wordmarks use ONE weight 600-800; tighten tracking `letter-spacing: -0.02em` (Latin) or 0 (Hangul); Korean names: bold geometric Hangul (Pretendard 700, Noto Sans KR 700, Black Han Sans for playful). SVG `<text>` depends on installed fonts: give a stack (`font-family="Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', system-ui, sans-serif"`) and tell the user to convert to outlines for print.
6. Color by industry (pick hue + feel): finance/legal = navy `#0b2a5b` + gold `#c8a24a`; tech/SaaS = indigo `#4f46e5` or electric blue `#2563eb` + slate; health/wellness = teal `#0d9488` / green `#16a34a` + soft white; food/cafe = warm brown `#7c4a2d`, tomato `#e4572e`, cream `#fff4e0`; kids/education = sun `#ffc43d`, sky `#38bdf8`, coral `#ff6b6b`; luxury/fashion = black `#111` + off-white `#f5f1ea` (+ thin serif); eco = forest `#14532d` + sand `#e7dcc3`; gaming = violet `#7c3aed` + neon `#22d3ee` on near-black.
7. Contrast: mark on its background >= 3:1 (UI) and text >= 4.5:1. Dark variant: swap ink to `#f5f7fb`, keep accent, lighten if needed; deliver `prefers-color-scheme` aware via CSS variables or two files.
8. Small sizes: at 16/32px drop details, thicken strokes (>= 2px at 16px), no text in favicons beyond 1-2 letters.
9. No clip art, no gradients+shadow+3D, no stock-looking swooshes, no emoji. Avoid cliches (lightbulb, globe) unless twisted.
10. Invent a name only if the user gave none; otherwise use THEIR name in the logo.

## Example (combination mark, copy and adapt: cafe "모닝브루")
```html
<svg viewBox="0 0 240 64" width="240" height="64" role="img" aria-labelledby="t1" xmlns="http://www.w3.org/2000/svg">
  <title id="t1">모닝브루 로고</title>
  <rect x="2" y="2" width="60" height="60" rx="16" fill="#7c4a2d"/>
  <path d="M18 28h24v8a12 12 0 0 1-24 0z" fill="#fff4e0"/>
  <path d="M42 30h4a5 5 0 0 1 0 10h-4" fill="none" stroke="#fff4e0" stroke-width="3" stroke-linecap="round"/>
  <path d="M25 24c0-3 3-3 3-6M33 24c0-3 3-3 3-6" fill="none" stroke="#e4572e" stroke-width="3" stroke-linecap="round"/>
  <text x="76" y="42" font-family="Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif" font-size="26" font-weight="800" fill="#7c4a2d">모닝브루</text>
</svg>
```

## Favicon + app icon set (head)
```html
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#7c4a2d">
```
Sizes: favicon.svg (vector, any), 32x32, 180x180 apple-touch (no transparency, solid bg, no rounded corners: the OS rounds), 192 and 512 PNG for the manifest (maskable: logo inside central 80%), 1200x630 social card, avatar 400x400 (circle crop: keep mark inside central 70%). Single-file shortcut: inline data-URI icon `<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%237c4a2d'/%3E%3C/svg%3E">` (escape `<` `>` `#`).

## Pitfalls
- `<text>` without a font stack renders in Times; Hangul glyphs need a Korean font present.
- SVG used as `<img>` cannot load web fonts or external CSS; inline it or outline text.
- Duplicate `id` values across several inline logos break gradients; prefix ids per logo.
- Dark mode logos on dark pages: use `currentColor` or CSS variables on `fill`, not hard-coded dark ink.
- More: reference/logo-examples.md (6 finished SVG logos), reference/brand-guide.md (mini guide template, variants, social avatar).
