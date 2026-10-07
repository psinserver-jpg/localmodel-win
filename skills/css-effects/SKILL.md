---
name: css-effects
description: Modern visual effects in pure CSS - glassmorphism, gradients, glow, grain, gradient borders, realistic shadows, 3D transforms, tilt cards, clip-path, scroll-driven effects. Use for fancy, premium, eye-catching styling of any page or component.
triggers: [glassmorphism, glass effect, frosted glass, backdrop-filter, neumorphism, gradient, mesh gradient, glow, neon, noise, grain, gradient border, box-shadow, text gradient, 3d transform, card flip, tilt, parallax, clip-path, blend mode, css effect, visual effect, 글래스모피즘, 유리 효과, 그라데이션, 네온, 글로우, 그림자, 노이즈, 3d 효과, 카드 뒤집기, 패럴랙스, 시각 효과, 효과, 블러, 뉴모피즘]
priority: 45
---
# CSS Effects

Pure CSS, single file, no build. Pick ONE effect family per page; effects are seasoning, not the meal.

## Hard rules
1. Define colors as tokens in `:root`; effects use `rgb(... / alpha)` or `color-mix()`.
2. Glass needs something colorful BEHIND it (gradient/blob/image). On a flat bg it looks like nothing.
3. Glass = `background: rgb(255 255 255 / .12); backdrop-filter: blur(16px) saturate(160%); border: 1px solid rgb(255 255 255 / .25);` ALWAYS add `-webkit-backdrop-filter` and an `@supports not (backdrop-filter: blur(1px))` fallback with a solid `rgb(30 32 48 / .92)` bg.
4. Text on glass must still reach 4.5:1: put glass over a darkened gradient, text `#fff`.
5. Animate only `transform` and `opacity` (GPU). Never animate `box-shadow` blur, `width`, `top` on many elements; fade a pseudo-element's opacity instead.
6. Wrap motion in `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }`.
7. Blur radius ≤ 24px, max ~6 blurred layers on screen (phones lag). `will-change` only on the element animating.
8. Real shadows = 2-4 stacked layers, low alpha, same hue as bg (not pure black): `0 1px 2px rgb(16 24 40 / .08), 0 4px 8px rgb(16 24 40 / .08), 0 16px 32px rgb(16 24 40 / .10)`.
9. Neumorphism only for 1-2 decorative widgets (toggle, knob); low contrast fails accessibility. Never for buttons that need to read as clickable.
10. Korean text: `word-break: keep-all`; glow/gradient text keeps `font-weight >= 700`.
11. Glow = `text-shadow: 0 0 8px currentColor, 0 0 24px color-mix(in srgb, currentColor 60%, transparent)` on a DARK bg (#0a0a14).

## Compact recipe (glass card over mesh gradient)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>글래스 카드</title>
<style>
:root { --ink:#fff; --bg:#0b1020; --a:#7c3aed; --b:#06b6d4; --c:#f43f5e; }
* { box-sizing: border-box; }
body { margin:0; min-height:100svh; display:grid; place-items:center; color:var(--ink);
  font-family:"Pretendard Variable",Pretendard,system-ui,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  word-break:keep-all; background:
    radial-gradient(at 20% 15%, var(--a) 0, transparent 50%),
    radial-gradient(at 80% 25%, var(--b) 0, transparent 45%),
    radial-gradient(at 50% 90%, var(--c) 0, transparent 50%), var(--bg); }
.glass { width:min(92vw,22rem); padding:2rem; border-radius:24px;
  background:rgb(255 255 255 / .12); border:1px solid rgb(255 255 255 / .25);
  -webkit-backdrop-filter:blur(16px) saturate(160%); backdrop-filter:blur(16px) saturate(160%);
  box-shadow:0 8px 32px rgb(0 0 0 / .25), inset 0 1px 0 rgb(255 255 255 / .35); }
@supports not (backdrop-filter: blur(1px)) { .glass { background:rgb(30 32 48 / .92); } }
.glass h1 { margin:0 0 .5rem; font-size:1.5rem; }
.glass p { margin:0 0 1.25rem; line-height:1.7; opacity:.9; }
.btn { min-height:44px; padding:.75rem 1.25rem; border:0; border-radius:12px; font:inherit; font-weight:700;
  color:#0b1020; background:#fff; cursor:pointer; transition:transform .2s; }
.btn:hover { transform:translateY(-2px); }
.btn:focus-visible { outline:3px solid #fff; outline-offset:3px; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style></head>
<body><div class="glass"><h1>오늘의 추천</h1><p>은은하게 비치는 유리 질감의 카드입니다.</p><button class="btn">자세히 보기</button></div></body></html>
```

## Quick snippets
- Gradient text: `.gt { background:linear-gradient(90deg,#7c3aed,#06b6d4); -webkit-background-clip:text; background-clip:text; color:transparent; }`
- Outline text: `-webkit-text-stroke: 2px #fff; color: transparent;`
- Gradient border (rounded, works with transparent bg): `border:2px solid transparent; background:linear-gradient(var(--bg),var(--bg)) padding-box, linear-gradient(135deg,#7c3aed,#06b6d4) border-box;`
- Clip shapes: `clip-path: polygon(0 0,100% 0,100% 85%,0 100%);` / `circle(50%)` / `inset(0 round 24px)`.
- Blend: `mix-blend-mode: multiply` (darken on light), `screen` (glow on dark), `overlay` (contrast); `background-blend-mode: overlay` for tinting photos.
- Conic spinner border: `background: conic-gradient(from 0deg,#7c3aed,#06b6d4,#7c3aed)` + `mask`.
- Scroll reveal, no JS: `@supports (animation-timeline: view()) { .rv { animation: rv linear both; animation-timeline: view(); animation-range: entry 0% cover 30%; } } @keyframes rv { from { opacity:0; transform:translateY(40px); } to { opacity:1; transform:none; } }` (content stays visible where unsupported).

## Pitfalls
- `backdrop-filter` does nothing if the element or ancestor has `overflow:hidden` + `border-radius` clipped oddly, or if bg is fully opaque. Keep alpha bg.
- `overflow:hidden` on parent kills `position: sticky`. Gradient text with `color:transparent` and no `background-clip` = invisible text.
- `transform-style: preserve-3d` is broken by `overflow:hidden`, `filter`, or `opacity<1` on the same element.
- Heavy `filter: blur()` on full-screen animated elements drops mobile to 20fps; blur a static layer, animate its `transform`.
- More recipes: reference/recipes.md (noise, neon, neumorphism, 3D flip, tilt JS, parallax, masks). Full-screen demos: reference/3d-and-motion.md.
