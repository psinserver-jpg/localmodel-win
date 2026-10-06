---
name: web-design
description: Build beautiful modern accessible websites and UIs (landing pages, portfolios, dashboards, blogs, shops, app screens) as complete runnable HTML/CSS/JS, Tailwind or React. Use for any web page, frontend, UI or visual design task.
triggers: [website, web site, web page, webpage, landing page, homepage, html, css, ui, ux, design, frontend, front-end, portfolio, dashboard, admin panel, blog, online shop, e-commerce, product page, pricing page, navbar, hero section, layout, responsive, dark mode, tailwind, react component, single page, one page, 웹사이트, 홈페이지, 랜딩페이지, 디자인, 웹페이지, 웹 디자인, 프론트엔드, 포트폴리오, 대시보드, 관리자 페이지, 쇼핑몰, 블로그, 버튼, 레이아웃, 반응형, 다크모드, 화면, 퍼블리싱, 상세페이지, 회사 소개]
priority: 50
---
# Web Design Skill

You are building a real website that a client will ship. It must look designed by a professional, work on phone and desktop, be accessible, and run without errors. Follow these rules in order.

## 1. Decide before you code
Write a short design brief as a CSS comment at the top of the stylesheet. Fill every line:
```
/* BRIEF  purpose: ... | audience: ... | tone: (e.g. calm, premium, playful, technical)
   direction: ONE visual direction (e.g. "editorial serif, warm paper, lots of whitespace")
   palette: neutral + primary + accent hex | fonts: heading / body | radius: 4|8|16px */
```
- Pick ONE direction and apply it everywhere. Never mix styles (e.g. glassmorphism cards + brutalist buttons).
- Derive tone from the business: law firm = restrained serif; kids app = rounded, bright; dev tool = dense, monospace accents.
- Write all visible copy in the user's language.
- Write realistic, specific copy: real-sounding product names, prices, dates, addresses, numbers ("2,400 teams", "Opens 11:30"). Never lorem ipsum, never "Feature 1".

## 2. Design tokens (CSS custom properties)
Define all colors, fonts, sizes, spacing, radius and shadows once in `:root`. Use only tokens in components; no raw hex below the token block.
- Palette = 1 neutral scale (bg, surface, surface-2, border, text, text-muted) + 1 primary + 1 accent. Max 3 hues total plus red/green/amber for status only.
- 60-30-10: 60% background/neutral, 30% surface/secondary, 10% primary+accent (buttons, links, key highlights). The primary is rare and therefore meaningful.
- Contrast (WCAG AA): body text ≥ 4.5:1; large text (≥24px, or ≥18.66px bold) ≥ 3:1; UI boundaries, icons, focus rings ≥ 3:1.
- Safe facts: `#767676` is the lightest gray allowed for text on white (4.54:1). `#9ca3af` on white fails (2.5:1). White text on `#3b82f6` fails (3.7:1); use `#2563eb` (5.2:1) or darker. White on `#10b981` green fails; use `#047857`. Yellow/amber buttons need dark text.
- Never use pure `#000` on pure `#fff` for large areas; use `#111`–`#1a1a1a` text on `#fff`/`#fafafa`.
- Dark mode: redefine the same tokens inside `@media (prefers-color-scheme: dark) { :root { ... } }`. Dark bg `#0b0d10`–`#18181b` (not pure black), text `#e5e7eb`-ish, lighten the primary until it passes 4.5:1 on the dark bg, and use dark text on bright primary buttons. Add `color-scheme: light dark;` on `:root`.

## 3. Typography
- Max 2 families (one heading, one body); one family is fine. Load at most 3–4 weights (400, 500/600, 700).
- Type scale ratio 1.25: 0.8rem, 1rem, 1.25rem, 1.563rem, 1.953rem, 2.441rem, 3.052rem. Body = 1rem (16px) minimum; 1.0625–1.125rem for reading pages.
- Fluid headings: h1 `clamp(2.25rem, 1.6rem + 3.2vw, 4rem)`, h2 `clamp(1.75rem, 1.3rem + 2vw, 2.75rem)`, h3 `clamp(1.25rem, 1.1rem + 0.8vw, 1.5rem)`.
- Line-height: body 1.6 (Korean 1.7), headings 1.1–1.25. Heading `letter-spacing: -0.02em` for Latin; `-0.01em` or 0 for Korean. `text-wrap: balance` on headings, `text-wrap: pretty` on paragraphs.
- Measure: paragraphs `max-width: 65ch` (60–75 characters; ≈35–45 Hangul characters).
- Font stacks:
  - Latin UI: `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
  - Korean: Pretendard via jsDelivr `<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">` then `font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;`. Alternative: Noto Sans KR from Google Fonts `https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap`.
  - Korean text: `word-break: keep-all; overflow-wrap: anywhere;` on body so words do not split mid-syllable. Set `<html lang="ko">`.
- Hierarchy through size + weight + color, not through many fonts. Muted text uses `--text-muted`, never opacity below 0.7.

## 4. Spacing and sizing
- Use a 4/8px scale only: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128px (as `--space-1`… tokens). No 13px, 22px, 37px.
- Section padding: `padding-block: clamp(4rem, 8vw, 8rem)`. Space between a heading and its content: 16–24px; between groups: 48–64px.
- Container: `width: min(100% - 2rem, 72rem); margin-inline: auto;` (1152px). Text-only container 45rem (720px).
- Proximity rule: related items closer together than unrelated items. Inner padding of a card ≤ the gap between cards' sections.

## 5. Layout
- Mobile-first: base CSS for 360px wide phones, then `@media (min-width: 640px)`, `768px`, `1024px`, `1280px`.
- Flexbox for one dimension (nav, button rows), Grid for two (card grids, page shells).
- Responsive grid without media queries: `grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); gap: 1.5rem;`.
- No horizontal scroll at 320px: `img, svg, video { max-width: 100%; height: auto; }`, never `width: 100vw`, add `min-width: 0` to grid/flex children that hold long text, tables in `overflow-x: auto` wrappers.
- Use `min-height: 100svh` (not `100vh`) for full-screen heroes.
- Split heroes stack on mobile (text first), go 2-column at ≥ 900px.

## 6. Visual hierarchy and composition
- Each screen has ONE primary action. One filled primary button per view; the second action is outline or ghost.
- Size contrast: h1 is ≥ 2.5× body size. Eyebrow labels 0.8rem uppercase `letter-spacing: 0.08em` (skip uppercase for Korean).
- Align to a grid: left-align body text; center only short hero/CTA blocks (≤ 3 lines).
- Vary section rhythm: alternate background (bg / surface), alternate layouts (split, grid, single column, full-bleed quote). Never 6 identical sections in a row.
- Whitespace is a feature: when in doubt, add space, not borders.

## 7. Components and states
- Every interactive element has `:hover`, `:focus-visible`, `:active`, and `:disabled`/`[aria-disabled="true"]` styles. Focus ring: `outline: 2px solid var(--focus); outline-offset: 2px;`. Never `outline: none` without a replacement.
- Buttons: `<button>` for actions, `<a>` for navigation. min-height 44px, padding `0.75rem 1.25rem`, weight 600, radius = token. Variants: primary (filled), secondary (outline), ghost.
- Radius system: pick one base (4, 8 or 12px); inputs and buttons use it, cards use base or 1.5×, pills use 999px. Shadows: max 3 levels (sm, md, lg), soft and low-opacity (e.g. `0 1px 2px rgb(0 0 0 / .06), 0 4px 12px rgb(0 0 0 / .06)`).
- Nav: `<header><nav aria-label="Main">`; below 768px a `<button aria-expanded="false" aria-controls="menu">` toggles the menu; close on Escape and on link click. Logo links to `#top` or `/`.
- Cards: consistent padding (24px), one heading, max 3 lines of text, one action. Whole-card link via a stretched `::after` on the heading link.
- Forms: every input has a visible `<label for>`; placeholder is not a label. Input height ≥ 44px, `font-size: 1rem` (prevents iOS zoom). Error text below field, red + icon/text (not color alone), linked with `aria-describedby`. Use correct `type` (`email`, `tel`, `number`) and `autocomplete`.

## 8. Imagery and icons (no broken assets)
- Prefer assets that cannot break: inline SVG illustrations, CSS gradients/shapes, `<svg>` patterns, CSS-only device mockups.
- Icons: inline SVG, `viewBox="0 0 24 24"`, `fill="none" stroke="currentColor" stroke-width="2"`, decorative ones get `aria-hidden="true"`. Same stroke width and size (20 or 24px) everywhere. Do not mix icon styles. Do not use emoji as icons except sparingly in playful/casual designs.
- Photos only if required: `https://picsum.photos/seed/<word>/800/600` (random content, needs internet). `source.unsplash.com` is shut down; do not use it. Always set `width`, `height`, `alt`, `loading="lazy"` (except the hero), and `object-fit: cover`. Give the container a background color so a failed image still looks intentional.
- Gradients: subtle, 2 close hues, or a soft radial glow behind the hero. Not on every element.

## 9. Motion
- Durations 150–300ms; easing `cubic-bezier(.2,.7,.2,1)` or `ease-out`. Animate only `transform` and `opacity` (and colors).
- Hover lift max `translateY(-2px)`. No infinite animations on content; no parallax by default.
- Always include: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; } }`.
- Scroll-reveal content must be visible without JS (add the hidden state via a `.js` class on `<html>`).

## 10. Accessibility and semantics
- Landmarks: `<header>`, `<nav>`, `<main id="main">`, `<footer>`; `<section>` with a heading. One `<h1>`; headings never skip levels.
- First focusable element: skip link `<a class="skip-link" href="#main">`.
- `<html lang="...">`, `<title>`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<meta charset="utf-8">`, `<meta name="description">`.
- Every `<img>` has `alt` (empty `alt=""` if decorative). Icon-only buttons have `aria-label`.
- Use native elements first (`<button>`, `<details>`, `<dialog>`, `<a href>`). Add ARIA only when no native element exists. No `<div onclick>`.
- Touch targets ≥ 44×44px with ≥ 8px between them.

## 11. Avoid the generic AI look
- No purple-to-blue gradient on everything; no gradient text on every heading.
- No 12 identical icon cards; group features into 3–6 with real differences, or use a list/split layout.
- No glassmorphism over plain white, no random blobs, no drop shadow on everything.
- No vague copy ("Unlock your potential", "Revolutionize your workflow"). State concrete benefits with numbers.
- No inconsistent radii/shadows; no centered paragraphs longer than 3 lines; no all-caps body text.
- No fake-looking stats ("1000000+ users"); use plausible specific numbers.
- Give the page character: one distinctive move (a bold type choice, an unusual accent color, an editorial grid, a signature illustration) executed consistently.

## 12. Deliverable rules
- Output complete, runnable files. No placeholders, no `TODO`, no "add your content here", no `...` omitted code.
- Default: a single `index.html` with `<style>` and `<script>` inline, or `index.html` + `styles.css` + `script.js` when asked for files. State each filename clearly.
- Must work opened directly from disk (`file://`): no `fetch()` of local files, no `type="module"` imports of local files, no build step unless the user asked for React/Vite. CDN links (fonts, Tailwind) are fine.
- Every `href="#id"` has a matching `id`. No `href="#"` dead links; use `<button>` for actions.
- JS: wrap in `document.addEventListener('DOMContentLoaded', …)` or place `<script>` at end of body (or `defer`); check elements exist before using them; zero console errors.
- Footer year: render via JS or hardcode the current year.
- Before finishing, check the result against the review checklist: contrast, focus styles, mobile layout at 360px, no horizontal scroll, all states, reduced motion, valid HTML nesting.
