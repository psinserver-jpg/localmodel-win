# Web Design Review Checklist

## Document and deliverable
- [ ] File starts with `<!doctype html>` and `<html lang="...">` whose language matches the visible copy (e.g. `lang="ko"` for Korean)
- [ ] `<meta charset="utf-8">` and `<meta name="viewport" content="width=device-width, initial-scale=1">` present in `<head>`
- [ ] `<title>` and `<meta name="description">` contain real, page-specific text
- [ ] Code is complete: no `TODO`, `lorem ipsum`, "placeholder", "your text here", `...` or omitted sections
- [ ] All visible copy is in the user's language and uses specific, realistic names, numbers and details
- [ ] Every `href="#x"` has a matching element with `id="x"`; no `href="#"` or `href=""` on links
- [ ] No local `fetch()`, no `<script type="module" src="./...">` and no build step unless React/Vite was requested (works from `file://`)
- [ ] Every external URL is a known CDN (Google Fonts, jsDelivr, cdn.tailwindcss.com, unpkg, picsum.photos); none use `source.unsplash.com`

## Design tokens and color
- [ ] A `:root` block defines color, font, spacing, radius and shadow custom properties
- [ ] Component CSS uses `var(--...)` tokens; raw hex/rgb values appear only inside token blocks
- [ ] Palette has at most one primary and one accent hue (plus status colors)
- [ ] Body text contrast is ≥ 4.5:1 against its background (light and dark mode)
- [ ] Muted/secondary text contrast is ≥ 4.5:1 (e.g. not `#9ca3af` on white)
- [ ] Button label contrast is ≥ 4.5:1 against the button fill (e.g. no white text on `#3b82f6` or on amber/yellow)
- [ ] Input borders, icons and focus ring have ≥ 3:1 contrast against adjacent colors
- [ ] `@media (prefers-color-scheme: dark)` redefines the color tokens (or the user explicitly asked for a single theme) and `color-scheme` is set

## Typography
- [ ] At most 2 font families loaded, with at most 4 weights, each with a system fallback stack
- [ ] Korean pages use Pretendard or Noto Sans KR (or a Korean system stack) and `word-break: keep-all`
- [ ] Base body font-size is ≥ 1rem (16px) and body `line-height` is between 1.5 and 1.8
- [ ] Headings use `clamp()` or breakpoint-based sizes and have `line-height` between 1.05 and 1.3
- [ ] Paragraph text has a `max-width` between 55ch and 75ch (or an equivalent container ≤ 45rem)
- [ ] Exactly one `<h1>`; heading levels never skip (no `h2` → `h4`)

## Layout and spacing
- [ ] Spacing values come from a 4/8px-based scale (tokens or multiples of 0.25rem)
- [ ] A container limits content width (e.g. `max-width`/`min()` around 64–80rem) with side padding ≥ 1rem on mobile
- [ ] CSS is mobile-first: base styles target small screens; layout changes use `min-width` media/container queries
- [ ] Multi-column layouts collapse to one column under ~640px (grid `minmax(min(100%, X), 1fr)` or media query)
- [ ] `img, svg, video` have `max-width: 100%`; no element uses `width: 100vw` or a fixed width > 360px without a wrapper
- [ ] Wide content (tables, code blocks) sits in an `overflow-x: auto` wrapper
- [ ] Sections alternate background or layout; no more than 3 visually identical sections in a row

## Components and interaction
- [ ] Buttons and links have distinct `:hover`, `:focus-visible` and `:active` styles; disabled controls have a disabled style
- [ ] No `outline: none`/`outline: 0` without a visible `:focus-visible` replacement
- [ ] Actions use `<button type="button">` (or `type="submit"` in forms); navigation uses `<a href>`; no clickable `<div>`/`<span>`
- [ ] Buttons, nav links and form controls have min-height ≥ 44px (or padding producing ≥ 44px)
- [ ] Mobile nav toggle is a `<button>` with `aria-expanded` and `aria-controls` that JS updates; menu closes on Escape
- [ ] Border-radius and box-shadow values come from ≤ 3 tokens each and are applied consistently
- [ ] Transitions are 100–400ms and animate only `transform`, `opacity`, colors or shadows
- [ ] `@media (prefers-reduced-motion: reduce)` disables or shortens animations and smooth scrolling

## Forms
- [ ] Every input, select and textarea has an associated `<label for>` (placeholder is not the only label)
- [ ] Inputs use correct `type` (`email`, `tel`, `url`, `number`) and `autocomplete` attributes
- [ ] Input font-size is ≥ 1rem (16px)
- [ ] Error messages are text (not color alone) and linked to the field via `aria-describedby` or shown via `:user-invalid`

## Media, icons and accessibility
- [ ] Every `<img>` has `alt` (descriptive, or `alt=""` if decorative), plus `width` and `height`
- [ ] Decorative inline SVGs have `aria-hidden="true"`; icon-only buttons/links have `aria-label`
- [ ] Icons share one style (same stroke width, size and `currentColor`); no mixed emoji/SVG icon sets
- [ ] Page uses `<header>`, `<nav>`, `<main>` and `<footer>` landmarks
- [ ] A skip link to `#main` is the first focusable element
- [ ] ARIA is used only where no native element fits (`<details>`, `<dialog>`, `<button>` preferred); no invalid ARIA roles

## Script quality
- [ ] Script runs after the DOM exists (`defer`, end of `<body>`, or `DOMContentLoaded`)
- [ ] Every `querySelector` result is null-checked or guaranteed by the markup; no undefined variables or functions
- [ ] Page content is visible and usable with JavaScript disabled (no content hidden until JS runs)
