---
name: responsive-accessibility
description: Breakpoint strategy, fluid type, touch targets, keyboard navigation, focus management, ARIA rules, contrast table and reduced motion.
triggers: [responsive, mobile, tablet, breakpoint, media query, accessibility, a11y, aria, keyboard, focus, screen reader, contrast, wcag, touch, 반응형, 모바일, 태블릿, 접근성, 키보드, 스크린리더, 명도대비]
---
# Responsive Design & Accessibility

## 1. Responsive strategy

- Write mobile styles first (no media query), then add `min-width` queries. Never design desktop-first and patch mobile.
- Breakpoints (use content, not devices): `40rem` (640px) large phone, `48rem` (768px) tablet, `64rem` (1024px) laptop, `80rem` (1280px) desktop.
- Test mentally at 360px, 768px, 1280px widths. At 360px nothing may overflow horizontally.
- Prefer intrinsic layouts that need no breakpoint:

```css
.grid-auto { display: grid; gap: var(--space-6, 1.5rem);
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
.stack > * + * { margin-block-start: var(--space-4, 1rem); }
.cluster { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }
.container { width: min(100% - 2rem, 72rem); margin-inline: auto; }
```

- `min(100%, 16rem)` prevents grid items overflowing on tiny screens.
- Container queries for components reused in different widths:

```css
.card-wrap { container-type: inline-size; }
@container (min-width: 32rem) { .card { display: grid; grid-template-columns: 12rem 1fr; } }
```

### Overflow killers (check every page)
- `img, svg, video { max-width: 100%; height: auto; display: block; }`
- Long words/URLs: `overflow-wrap: anywhere;` on text containers.
- Korean text: `word-break: keep-all;` so words are not split mid-syllable-group.
- Tables: wrap in `<div style="overflow-x:auto">`.
- Never set fixed `width` in px on layout boxes; use `max-width`.
- `100vw` includes the scrollbar → horizontal scroll. Use `100%` instead.
- Mobile viewport height: use `min-height: 100svh` (fallback `100vh` line before it).

## 2. Fluid typography

```css
:root {
  --step--1: clamp(0.83rem, 0.80rem + 0.15vw, 0.94rem);
  --step-0:  clamp(1rem,    0.95rem + 0.25vw, 1.13rem);
  --step-1:  clamp(1.2rem,  1.10rem + 0.50vw, 1.5rem);
  --step-2:  clamp(1.44rem, 1.25rem + 0.90vw, 2rem);
  --step-3:  clamp(1.73rem, 1.40rem + 1.60vw, 2.67rem);
  --step-4:  clamp(2.07rem, 1.50rem + 2.80vw, 3.55rem);
}
```

- Body never below 16px (1rem). Line length 60–75ch: `max-width: 65ch` on paragraphs.
- Always include `rem` in clamp middle values so user zoom still works.

## 3. Touch & pointer

- Interactive targets at least 44×44px: `min-height: 44px; padding-inline: 1rem;`.
- At least 8px between adjacent targets.
- Never rely on hover alone; anything revealed on hover must also appear on focus and be reachable on touch.
- Use `@media (hover: hover)` to scope hover-only effects.

## 4. Semantics first (ARIA last)

- One `<h1>` per page. Headings never skip levels (h2 → h4 is wrong).
- Landmarks: `<header>`, `<nav aria-label="주요 메뉴">`, `<main id="main">`, `<footer>`.
- Buttons do actions (`<button type="button">`), links go places (`<a href>`). Never `<div onclick>`.
- Every form control has a `<label for>`. Placeholder is not a label.
- Images: meaningful → descriptive `alt`; decorative → `alt=""`. Inline decorative SVG → `aria-hidden="true" focusable="false"`.
- Icon-only buttons need an accessible name: `<button aria-label="메뉴 열기">`.
- First rule of ARIA: if a native element exists (`<button>`, `<dialog>`, `<details>`), use it instead of ARIA.
- Allowed ARIA you will commonly need: `aria-expanded`, `aria-controls`, `aria-current="page"`, `aria-label`, `aria-live="polite"`, `aria-invalid`, `aria-describedby`.

## 5. Keyboard & focus

- Everything usable with Tab / Shift+Tab / Enter / Space / Esc.
- Never remove outlines without replacement:

```css
:focus-visible { outline: 3px solid var(--color-primary, #2563eb); outline-offset: 3px; border-radius: 4px; }
```

- Skip link as first element in `<body>`:

```html
<a class="skip-link" href="#main">본문 바로가기</a>
```
```css
.skip-link { position: absolute; left: 1rem; top: -3rem; padding: .5rem 1rem; background: #000; color: #fff; z-index: 100; }
.skip-link:focus { top: 1rem; }
```

- Tab order follows DOM order. Do not use positive `tabindex`.
- Modals: use `<dialog>` + `showModal()` (traps focus, Esc closes). Return focus to the opener on close.
- Mobile menu toggle: `aria-expanded` toggles true/false; Esc closes; menu links close the menu on click.
- Sticky headers: add `scroll-margin-top` to anchored sections so headings are not hidden: `section[id] { scroll-margin-top: 5rem; }`.

## 6. Color contrast quick table (WCAG AA)

| Use | Minimum ratio |
|---|---|
| Body text (< 24px, or < 18.66px bold) | 4.5 : 1 |
| Large text (≥ 24px, or ≥ 18.66px bold) | 3 : 1 |
| UI borders, icons, focus ring | 3 : 1 |

Known-safe pairs:
- `#111827` on `#ffffff` ≈ 17:1 · `#374151` on `#ffffff` ≈ 10:1 · `#6b7280` on `#ffffff` ≈ 4.8:1 (lightest gray allowed for text)
- `#ffffff` on `#2563eb` ≈ 5.2:1 · `#ffffff` on `#1d4ed8` ≈ 6.7:1
- `#e5e7eb` on `#111827` ≈ 14:1 · `#9ca3af` on `#111827` ≈ 6.9:1
- Unsafe: `#9ca3af` on white (≈ 2.5:1), white on `#f59e0b` (≈ 2.1:1), white on `#22c55e` (≈ 2.3:1). Use dark text on yellow/green/orange.
- Never use color alone for meaning (errors need text/icon too).

## 7. Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
```

- Durations 150–300ms; animate only `transform` and `opacity`.
- No auto-playing carousels; no flashing more than 3 times per second.

## 8. Forms

- `type="email"`, `type="tel"`, `inputmode="numeric"`, `autocomplete="name|email|tel|street-address"`.
- Show errors next to the field, connect with `aria-describedby`, set `aria-invalid="true"`.
- Announce submit results in a `role="status"` / `aria-live="polite"` region.
- Required fields: `required` attribute + visible marker explained once ("* 필수").

## 9. Final responsive/a11y check

- [ ] No horizontal scroll at 360px
- [ ] Nav usable on mobile (toggle works, `aria-expanded` updates)
- [ ] All images have `alt`; icon buttons have `aria-label`
- [ ] Visible `:focus-visible` style everywhere
- [ ] Heading levels in order, one `<h1>`
- [ ] Text contrast ≥ 4.5:1, UI ≥ 3:1
- [ ] `prefers-reduced-motion` respected
- [ ] Touch targets ≥ 44px
