---
name: layout-responsive
description: Mobile-first responsive layout recipes in plain CSS: container, fluid grids, holy grail, sidebar, bento, masonry-ish, sticky header/footer, hero/split screens, dashboards, container queries, safe areas and overflow bug fixes. Use for page structure, responsive design, grids and layout bugs.
triggers: [layout, responsive, mobile first, mobile-first, grid, css grid, flexbox, flex, breakpoint, media query, container query, sidebar, holy grail, bento, masonry, sticky header, sticky footer, hero layout, split screen, card grid, dashboard layout, viewport, 100vh, dvh, horizontal scroll, overflow, aspect ratio, safe area, landmarks, 레이아웃, 반응형, 모바일 우선, 그리드, 플렉스, 브레이크포인트, 미디어 쿼리, 사이드바, 벤토, 벤토 그리드, 메이슨리, 고정 헤더, 푸터 고정, 히어로, 화면 분할, 카드 목록, 대시보드 레이아웃, 가로 스크롤, 넘침, 화면 넘어감, 모바일 화면]
priority: 49
---
# Layout and Responsive

## Hard rules
1. Mobile-first: base CSS = 360px phone, single column. Add `@media (min-width: 640px | 768px | 1024px | 1280px)` only to enhance. Always `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. `*, *::before, *::after { box-sizing: border-box; }` and `img, svg, video { max-width: 100%; height: auto; }`.
3. Container: `.container { width: min(100% - 2rem, 72rem); margin-inline: auto; }` (text-only 45rem). Never fixed `width: 1200px`.
4. Flex for ONE axis (nav, button rows), Grid for TWO (page shell, card grids). Use `gap`, not margins between siblings.
5. Card grid without breakpoints: `grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); gap: 1.5rem;`. Always `min(100%, X)` inside minmax or it overflows below X px.
6. Fluid spacing: `padding-block: clamp(3rem, 2rem + 5vw, 7rem)`; gaps `clamp(1rem, .6rem + 1.5vw, 2rem)`. Spacing scale 4/8/12/16/24/32/48/64/96.
7. Full-height: `min-height: 100svh` (fallback line `min-height: 100vh` above it); app shells `height: 100dvh`. Never plain `100vh` on mobile.
8. Grid/flex children that hold long text or code need `min-width: 0` (else horizontal scroll). Tables/pre in `overflow-x: auto` wrappers. Never `width: 100vw` (includes scrollbar).
9. Images: set `width`/`height` attributes or `aspect-ratio: 16 / 9; object-fit: cover` to stop layout shift. Hero image `loading="eager"`, the rest `loading="lazy"`.
10. Text columns max 65ch; Korean text `word-break: keep-all; overflow-wrap: anywhere`.
11. Touch: targets >= 44px, spacing >= 8px between; sticky bars respect `env(safe-area-inset-*)` and viewport `viewport-fit=cover`.
12. Landmarks: one `<header>`, `<nav aria-label>`, one `<main id="main">`, `<aside>`, `<footer>`; add `<a class="skip" href="#main">본문 바로가기</a>`; h1 once, headings in order.
13. Show/hide by breakpoint only for navigation (hamburger < 768px). Don't hide content on mobile; reorder with `order` or grid areas.
14. Component-level responsiveness with container queries: `.card-wrap { container-type: inline-size; } @container (min-width: 28rem) { .card { grid-template-columns: 10rem 1fr; } }`. Fallback: media queries.
15. Test mentally at 320, 375, 768, 1024, 1440. Nothing may scroll horizontally.

## Page shell (copy, then pick a recipe from reference/layout-recipes.md)
```html
<body>
  <a class="skip" href="#main">본문 바로가기</a>
  <header class="site-header"><div class="container bar">
    <a class="logo" href="/">모아테크</a>
    <nav aria-label="주 메뉴"><a href="#features">기능</a><a href="#pricing">요금</a><a href="#faq">문의</a></nav>
  </div></header>
  <main id="main">
    <section class="hero"><div class="container hero__grid">
      <div><h1>팀의 일정을 한 곳에서</h1><p>회의, 마감, 휴가를 한 화면에서 확인해요.</p></div>
      <img src="hero.jpg" alt="일정 화면" width="800" height="600">
    </div></section>
    <section class="section"><div class="container grid-cards">
      <article class="card"><h3>자동 알림</h3><p>마감 하루 전에 알려줘요.</p></article>
      <article class="card"><h3>팀 캘린더</h3><p>모두의 일정을 한눈에.</p></article>
      <article class="card"><h3>간편 공유</h3><p>링크 하나로 공유해요.</p></article>
    </div></section>
  </main>
  <footer class="site-footer"><div class="container">© 2026 모아테크</div></footer>
</body>
```
```css
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; min-height: 100dvh; display: grid; grid-template-rows: auto 1fr auto; font-family: system-ui, sans-serif; line-height: 1.7; word-break: keep-all; }
img { max-width: 100%; height: auto; display: block; }
.container { width: min(100% - 2rem, 72rem); margin-inline: auto; }
.skip { position: absolute; left: -999px; } .skip:focus { left: 1rem; top: 1rem; background: #fff; padding: .5rem 1rem; z-index: 1000; }
.site-header { position: sticky; top: 0; z-index: 200; background: rgb(255 255 255 / .9); backdrop-filter: blur(8px); border-bottom: 1px solid #e5e7eb; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; min-height: 4rem; }
.bar nav { display: flex; gap: 1.25rem; flex-wrap: wrap; }
.section { padding-block: clamp(3rem, 2rem + 5vw, 7rem); }
.hero__grid { display: grid; gap: 2rem; align-items: center; }
.grid-cards { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
.card { padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; min-width: 0; }
@media (min-width: 900px) { .hero__grid { grid-template-columns: 1.1fr .9fr; gap: 4rem; } }
```

## Pitfalls
- `body { display:grid; grid-template-rows: auto 1fr auto }` gives sticky-footer for free; `main` must be the 1fr row.
- Sticky header + anchor links: `html { scroll-padding-top: 5rem; }`.
- `position: sticky` fails if an ancestor has `overflow: hidden/auto`; use `overflow: clip`.
- Flex children shrinking text: add `flex: 1 1 0; min-width: 0`.
- Fixed bottom bars cover content: add `padding-bottom` equal to bar height + `env(safe-area-inset-bottom)`.
- `vh` hero with iOS toolbars jumps; use `svh`.
- Do not use `float` or `table` layouts; no horizontal-scroll "desktop-only" pages.
- Recipes (holy grail, sidebar, bento, masonry, split, dashboard, container queries): reference/layout-recipes.md. Bug-fix catalog and a11y: reference/overflow-fixes.md.
