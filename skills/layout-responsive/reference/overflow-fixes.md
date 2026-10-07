---
name: overflow-fixes
description: Catalog of responsive layout bugs and fixes (horizontal scroll, 100vh on mobile, flex/grid overflow, sticky not working, images stretching, safe areas, z-index) plus a debugging snippet and accessibility landmark checklist.
triggers: [horizontal scroll, overflow, overflow-x, 100vh, dvh, svh, min-width 0, sticky not working, image stretched, layout broken, layout bug, mobile broken, safe area, notch, landmarks, skip link, accessibility, a11y, 가로 스크롤, 넘침, 레이아웃 깨짐, 모바일에서 깨져, 화면 밀림, 스크롤 생김, 이미지 찌그러, 고정 안 돼, 접근성, 노치]
---
# Layout bug catalog

## Find the element that causes horizontal scroll
Paste in the browser console, or keep it as a dev-only script:
```js
const docW = document.documentElement.clientWidth;
document.querySelectorAll('body *').forEach((el) => {
  const r = el.getBoundingClientRect();
  if (r.right > docW + 1 || r.left < -1) console.log('overflows:', el, Math.round(r.right - docW) + 'px');
});
```
Dev-only outline: `* { outline: 1px solid rgb(255 0 0 / .25); }`.

## Symptoms and fixes
| Symptom | Cause | Fix |
|---|---|---|
| Page scrolls sideways on phone | `width: 100vw`, fixed px widths, wide image/table/pre, negative margins | `width: 100%`, `max-width: 100%`, wrap table/pre in `overflow-x: auto`; last resort `html, body { overflow-x: clip; }` (hides, does not fix) |
| Long text/URL pushes grid/flex wider | children default `min-width: auto` | `min-width: 0` on the child; `overflow-wrap: anywhere` on text |
| Grid column overflows at 320px | `minmax(18rem, 1fr)` is wider than viewport | `minmax(min(100%, 18rem), 1fr)` |
| `1fr` column blows out with code/table | `1fr` = `minmax(auto, 1fr)` | `minmax(0, 1fr)` |
| Hero cut off / jumps on iOS | `100vh` includes browser toolbar | `min-height: 100vh; min-height: 100svh;` (app shells `100dvh`) |
| Image stretched/squished | width and height both set | `height: auto` or `aspect-ratio` + `object-fit: cover` |
| Image causes layout jump on load | no dimensions | `width`/`height` attrs, or `aspect-ratio: 16 / 9` on wrapper |
| `position: sticky` does nothing | ancestor has `overflow: hidden/auto`, or no `top`, or parent is as tall as the element | `overflow: clip` on ancestor, set `top: 0`, make parent taller |
| Anchor jumps under sticky header | header covers target | `html { scroll-padding-top: 5rem; }` |
| Footer floats mid-page on short pages | body not full height | `body { min-height: 100dvh; display: grid; grid-template-rows: auto 1fr auto; }` |
| Flex items shrink text into 1 char column | `flex-shrink` default | `flex: 0 0 auto` for icons; `flex: 1 1 0; min-width: 0` for text |
| Buttons wrap one letter per line | container too narrow | `white-space: nowrap` on labels; `flex-wrap: wrap` on the row |
| Modal scrolls the page behind | body scroll not locked | `body:has(dialog[open]) { overflow: hidden; }` and `overscroll-behavior: contain` on modal |
| Fixed bar hides last content | no padding | `padding-bottom: calc(var(--bar-h) + env(safe-area-inset-bottom))` |
| Text too small on phone | font-size in px < 16 on inputs | inputs `font-size: 1rem` (iOS zooms below 16px) |
| Tap target too small | 24px icon buttons | `min-width: 44px; min-height: 44px` with padding |
| Dropdown clipped by card | `overflow: hidden` on card | move overflow clipping to an inner wrapper; use `position: fixed` or `popover` |
| Gap looks double | margin + gap | use only `gap` |
| 100% height child collapses | parent has no height | grid with `grid-template-rows: auto 1fr`; or `height: 100%` chain up to `html` |
| Margin collapse surprises | adjacent vertical margins | `display: flow-root` on parent, or use `.stack > * + *` |
| Korean words break mid-word | default `word-break` | `word-break: keep-all; overflow-wrap: anywhere;` |

## Safe areas (notch, home indicator)
```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```
```css
.header { padding-top: env(safe-area-inset-top); padding-inline: max(1rem, env(safe-area-inset-left)) max(1rem, env(safe-area-inset-right)); }
.footer-fixed { padding-bottom: max(.75rem, env(safe-area-inset-bottom)); }
```

## Aspect ratio helpers
```css
.ratio-16x9 { aspect-ratio: 16 / 9; } .ratio-4x3 { aspect-ratio: 4 / 3; } .ratio-1x1 { aspect-ratio: 1; }
.cover { width: 100%; height: 100%; object-fit: cover; object-position: center; }
.video-wrap { aspect-ratio: 16 / 9; } .video-wrap iframe { width: 100%; height: 100%; border: 0; }
/* fallback for old browsers */
@supports not (aspect-ratio: 1) { .ratio-16x9 { height: 0; padding-top: 56.25%; position: relative; } }
```

## z-index discipline
Scale: content 0, dropdown 100, sticky 200, overlay 300, modal 400, toast 500. A stacking context (transform, opacity < 1, filter, `isolation: isolate`) traps children: if a dropdown hides behind another section, move it up the DOM or give its ancestor the higher z-index. Use `isolation: isolate` on components so inner z-indexes never leak.

## Responsive images and media
```html
<img src="cafe-800.jpg" srcset="cafe-480.jpg 480w, cafe-800.jpg 800w, cafe-1280.jpg 1280w"
     sizes="(min-width: 900px) 50vw, 100vw" width="800" height="600" alt="창가 자리가 있는 카페 내부" loading="lazy" decoding="async">
<picture><source media="(min-width: 900px)" srcset="wide.jpg"><img src="square.jpg" alt="제품 사진" width="600" height="600"></picture>
```
Without real image files use CSS gradients or inline SVG shapes so nothing 404s.

## Accessibility landmarks checklist
- Skip link first in body; `<main id="main" tabindex="-1">`.
- One `<h1>`; `<nav aria-label="주 메뉴">` (label every nav when more than one); `<aside aria-label="관련 글">`; `<footer>`.
- Visible focus on everything focusable; DOM order = visual order (do not rely on `order` for reading order of important content).
- Hamburger: `<button aria-expanded="false" aria-controls="menu">`; update `aria-expanded` in JS and close on Esc.
- `lang="ko"` on `<html>`; `alt=""` for decorative images; buttons are `<button>`, links are `<a href>`.
- Respect `@media (prefers-reduced-motion: reduce)` for sliding menus.

## Print and large screens
```css
@media (min-width: 1600px) { :root { font-size: 112.5%; } .container { width: min(100% - 4rem, 80rem); } }
@media print { header, footer, nav, .no-print { display: none !important; } body { color: #000; background: #fff; } a::after { content: " (" attr(href) ")"; } }
```
