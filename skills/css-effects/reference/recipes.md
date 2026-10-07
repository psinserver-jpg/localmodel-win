---
name: css-recipes
description: Copy-paste CSS recipes - noise grain overlay, neon glow, neumorphism, gradient borders, realistic shadows, clip-path and mask shapes, blend modes, animated gradients.
triggers: [noise, grain, neon, glow, neumorphism, soft ui, gradient border, shadow, elevation, clip-path, mask, blend mode, animated gradient, aurora, conic, 노이즈, 그레인, 네온, 뉴모피즘, 그림자, 마스크, 그라데이션 애니메이션, 오로라]
---
# CSS recipes

## Noise / grain overlay (SVG feTurbulence as data-URI, no image file)
```css
:root { --grain: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
body::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 50;
  background-image: var(--grain); opacity: .08; mix-blend-mode: overlay; }
```
`%23` replaces `#` inside the data-URI. Opacity .05-.12; higher looks dirty.

## Neon sign
```css
.neon { color: #e0f7ff; font-weight: 800; letter-spacing: .04em;
  text-shadow: 0 0 4px #fff, 0 0 12px #22d3ee, 0 0 28px #22d3ee, 0 0 56px #0891b2; }
.neon-box { border: 2px solid #f0abfc; border-radius: 16px;
  box-shadow: 0 0 6px #f0abfc, 0 0 24px #d946ef, inset 0 0 12px rgb(217 70 239 / .45); }
@keyframes flicker { 0%,19%,22%,62%,64%,100% { opacity: 1; } 20%,21%,63% { opacity: .55; } }
.neon.flicker { animation: flicker 4s infinite; }
```
Dark bg only (`#07070f`). Neon + small body text = unreadable; use for headings.

## Neumorphism (use sparingly)
```css
:root { --nm-bg: #e6e9ef; }
.nm { background: var(--nm-bg); border-radius: 20px;
  box-shadow: 8px 8px 16px #c3c7d0, -8px -8px 16px #ffffff; }
.nm:active, .nm.pressed { box-shadow: inset 6px 6px 12px #c3c7d0, inset -6px -6px 12px #ffffff; }
```
Why sparingly: element and bg are the same color, edge contrast about 1.2:1 (needs 3:1), so buttons are not obviously clickable. Add a text label, a colored icon, and a visible `:focus-visible` outline.

## Gradient border + glow on hover
```css
.gb { position: relative; border-radius: 20px; padding: 1.5rem; background: #12141f; color: #fff; }
.gb::before { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 2px;
  background: linear-gradient(135deg, #7c3aed, #06b6d4, #f43f5e);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none; }
.gb::after { content: ""; position: absolute; inset: -1px; border-radius: inherit; z-index: -1;
  background: linear-gradient(135deg, #7c3aed, #06b6d4); filter: blur(24px); opacity: 0; transition: opacity .3s; }
.gb:hover::after { opacity: .45; }
```

## Animated aurora background (transform only)
```css
.aurora { position: relative; overflow: hidden; background: #0b1020; }
.aurora i { position: absolute; width: 60vmax; height: 60vmax; border-radius: 50%; filter: blur(80px); opacity: .55;
  animation: drift 24s ease-in-out infinite alternate; }
.aurora i:nth-child(1) { background: #7c3aed; left: -15vmax; top: -15vmax; }
.aurora i:nth-child(2) { background: #06b6d4; right: -20vmax; top: 10vmax; animation-duration: 30s; }
.aurora i:nth-child(3) { background: #f43f5e; left: 20vmax; bottom: -30vmax; animation-duration: 36s; }
@keyframes drift { to { transform: translate(10vmax, 6vmax) scale(1.15); } }
```
HTML: `<div class="aurora"><i></i><i></i><i></i><main>...</main></div>` (give main `position: relative`).

## Shadows that look real
```css
:root {
  --shadow-1: 0 1px 2px rgb(15 23 42 / .08), 0 1px 3px rgb(15 23 42 / .06);
  --shadow-2: 0 2px 4px rgb(15 23 42 / .06), 0 8px 16px rgb(15 23 42 / .08);
  --shadow-3: 0 4px 8px rgb(15 23 42 / .06), 0 16px 32px rgb(15 23 42 / .10), 0 32px 64px rgb(15 23 42 / .10);
}
.card { box-shadow: var(--shadow-2); transition: transform .25s, box-shadow .25s; }
.card:hover { transform: translateY(-4px); box-shadow: var(--shadow-3); }
.float-shadow { filter: drop-shadow(0 12px 16px rgb(15 23 42 / .25)); }
```
`drop-shadow` follows transparent PNG/SVG/clip shapes; `box-shadow` does not.

## Shapes: clip-path and mask
```css
.slant { clip-path: polygon(0 0, 100% 0, 100% calc(100% - 4vw), 0 100%); }
.hex { aspect-ratio: 1; clip-path: polygon(50% 0, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%); }
.fade-bottom { -webkit-mask-image: linear-gradient(#000 70%, transparent); mask-image: linear-gradient(#000 70%, transparent); }
.spot { -webkit-mask-image: radial-gradient(circle at 50% 40%, #000 30%, transparent 70%); mask-image: radial-gradient(circle at 50% 40%, #000 30%, transparent 70%); }
.reveal { clip-path: inset(0 100% 0 0); animation: wipe .8s .2s cubic-bezier(.2,.8,.2,1) forwards; }
@keyframes wipe { to { clip-path: inset(0 0 0 0); } }
```

## Gradient text + shine sweep
```css
.shine { background: linear-gradient(110deg, #94a3b8 30%, #fff 50%, #94a3b8 70%); background-size: 250% 100%;
  -webkit-background-clip: text; background-clip: text; color: transparent; animation: sweep 3s linear infinite; }
@keyframes sweep { to { background-position: -250% 0; } }
```

## Blend modes
```css
.duotone { position: relative; isolation: isolate; }
.duotone img { display: block; width: 100%; filter: grayscale(1) contrast(1.1); }
.duotone::after { content: ""; position: absolute; inset: 0; background: linear-gradient(135deg, #4f46e5, #f43f5e); mix-blend-mode: screen; }
.hero-tint { background: url("hero.jpg") center/cover, #1e1b4b; background-blend-mode: multiply; }
```
Put `isolation: isolate` on the parent so blending does not leak to the page.
