---
name: layout-recipes
description: Copy-paste CSS layout recipes with HTML skeletons - holy grail, sidebar plus content, bento grid, masonry-ish columns, sticky header/footer, hero variants, split screen, card grids, dashboard shell, container queries, mobile bottom nav.
triggers: [holy grail, sidebar layout, bento grid, masonry, columns, sticky footer, sticky header, hero section, split screen, two column, card grid, dashboard layout, admin layout, container query, bottom navigation, tab bar, app shell, 레이아웃, 사이드바, 벤토, 메이슨리, 고정 푸터, 히어로, 화면 분할, 2단, 카드 그리드, 대시보드, 관리자 레이아웃, 하단 탭, 앱 레이아웃]
---
# Layout recipes
All mobile-first; add `*, *::before, *::after { box-sizing: border-box; }` and `body { margin: 0; }` once.

## 1. Holy grail (header, nav, main, aside, footer)
```html
<div class="shell">
  <header>헤더</header><nav aria-label="사이드 메뉴">메뉴</nav><main id="main">본문</main><aside>보조</aside><footer>푸터</footer>
</div>
```
```css
.shell { min-height: 100dvh; display: grid; grid-template-columns: minmax(0, 1fr);
  grid-template-areas: "h" "n" "m" "a" "f"; grid-template-rows: auto auto 1fr auto auto; }
.shell > header { grid-area: h; } .shell > nav { grid-area: n; } .shell > main { grid-area: m; padding: 1rem; }
.shell > aside { grid-area: a; } .shell > footer { grid-area: f; }
@media (min-width: 900px) {
  .shell { grid-template-columns: 14rem minmax(0, 1fr) 16rem;
    grid-template-areas: "h h h" "n m a" "f f f"; grid-template-rows: auto 1fr auto; }
}
```

## 2. Sidebar + content (collapsible on mobile)
```css
.layout { display: grid; grid-template-columns: minmax(0, 1fr); }
.sidebar { position: fixed; inset: 0 auto 0 0; width: min(18rem, 85vw); background: var(--surface, #fff); transform: translateX(-100%);
  transition: transform .25s cubic-bezier(.2, 0, 0, 1); z-index: 300; overflow-y: auto; }
.sidebar.is-open { transform: none; }
@media (min-width: 900px) {
  .layout { grid-template-columns: 16rem minmax(0, 1fr); }
  .sidebar { position: sticky; top: 0; height: 100dvh; transform: none; }
}
```
Toggle: `btn.addEventListener('click', () => sidebar.classList.toggle('is-open'))` and set `aria-expanded`.
Intrinsic sidebar without media query: `display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr))` or flex `.side { flex: 1 1 14rem } .main { flex: 999 1 30rem }` (wraps under when narrow).

## 3. Bento grid
```html
<section class="bento">
  <article class="b b--wide">핵심 기능</article><article class="b">알림</article><article class="b">보안</article>
  <article class="b b--tall">통계</article><article class="b">연동</article><article class="b b--wide">후기</article>
</section>
```
```css
.bento { display: grid; gap: 1rem; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-auto-rows: minmax(9rem, auto); grid-auto-flow: dense; }
.b { padding: 1.25rem; border-radius: 20px; background: var(--surface-2, #f1f3f6); overflow: hidden; }
.b--wide { grid-column: span 2; }
@media (min-width: 900px) {
  .bento { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1.25rem; }
  .b--tall { grid-row: span 2; }
}
```
Rules: 1 hero tile (span 2), vary spans, keep gap equal, same radius everywhere, `dense` fills holes.

## 4. Masonry-ish
CSS columns (simple, order flows down columns):
```css
.masonry { columns: 1; column-gap: 1rem; }
.masonry > * { break-inside: avoid; margin: 0 0 1rem; }
@media (min-width: 600px) { .masonry { columns: 2; } }
@media (min-width: 1000px) { .masonry { columns: 3; } }
```
Native masonry (progressive): `@supports (grid-template-rows: masonry) { .masonry { display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); grid-template-rows: masonry; columns: auto; } }`.
Image gallery with fixed ratio is more robust: `.gallery img { aspect-ratio: 4 / 3; object-fit: cover; width: 100%; }`.

## 5. Sticky header + footer + scrolling main
```css
body { min-height: 100dvh; display: grid; grid-template-rows: auto 1fr auto; margin: 0; }
header.top { position: sticky; top: 0; z-index: 200; }
html { scroll-padding-top: 4.5rem; }
```
App-like (only main scrolls): `body { height: 100dvh; overflow: hidden; } main { overflow-y: auto; overscroll-behavior: contain; }`.

## 6. Hero variants
```css
.hero { padding-block: clamp(3rem, 2rem + 8vw, 8rem); }
.hero--center { text-align: center; } .hero--center > .container > * { margin-inline: auto; max-width: 42rem; }
.hero--full { min-height: 100vh; min-height: 100svh; display: grid; place-items: center; }
.hero--bg { position: relative; isolation: isolate; color: #fff; }
.hero--bg::before { content: ""; position: absolute; inset: 0; z-index: -1; background: linear-gradient(rgb(0 0 0 / .45), rgb(0 0 0 / .65)), var(--hero-img) center / cover; }
.hero__actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.5rem; }
```
Split hero stacks on mobile (text first), 2 columns at >= 900px (see skeleton in SKILL.md). One primary CTA per hero.

## 7. Split screen (login, about)
```css
.split { min-height: 100dvh; display: grid; }
.split__art { min-height: 30dvh; background: linear-gradient(135deg, #2563eb, #0e7490); }
.split__form { display: grid; place-items: center; padding: 2rem 1rem; }
@media (min-width: 900px) { .split { grid-template-columns: 1fr 1fr; } .split__art { min-height: auto; } }
```

## 8. Card grid and card layouts
```css
.cards { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr)); }
.card { display: grid; grid-template-rows: auto 1fr auto; gap: .75rem; min-width: 0; }  /* footer buttons align across cards */
.card img { aspect-ratio: 16 / 10; object-fit: cover; width: 100%; border-radius: 12px 12px 0 0; }
.cards--fixed { grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); }  /* last row keeps column width */
```
auto-fit stretches a lone card to full width; use auto-fill if that looks wrong.

## 9. Dashboard shell
```html
<div class="dash">
  <aside class="dash__nav">메뉴</aside>
  <header class="dash__top">오늘의 현황</header>
  <main class="dash__main">
    <section class="kpis"><div class="kpi">방문자 12,480</div><div class="kpi">매출 3,240,000원</div><div class="kpi">전환율 4.2%</div><div class="kpi">이탈률 31%</div></section>
    <section class="panels"><div class="panel panel--lg">추이 차트</div><div class="panel">최근 주문</div></section>
  </main>
</div>
```
```css
.dash { min-height: 100dvh; display: grid; grid-template-columns: minmax(0, 1fr); grid-template-areas: "top" "main"; }
.dash__nav { display: none; grid-area: nav; }
.dash__top { grid-area: top; padding: 1rem; position: sticky; top: 0; z-index: 200; background: var(--surface, #fff); }
.dash__main { grid-area: main; padding: 1rem; display: grid; gap: 1rem; align-content: start; min-width: 0; }
.kpis { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 11rem), 1fr)); }
.panels { display: grid; gap: 1rem; }
.panel { padding: 1.25rem; border-radius: 12px; border: 1px solid var(--border, #e5e7eb); min-width: 0; overflow: auto; }
@media (min-width: 1024px) {
  .dash { grid-template-columns: 15rem minmax(0, 1fr); grid-template-areas: "nav top" "nav main"; }
  .dash__nav { display: block; position: sticky; top: 0; height: 100dvh; padding: 1rem; }
  .panels { grid-template-columns: 2fr 1fr; }
}
```
Charts: wrap canvas/svg in a div with a fixed `height` (e.g. `18rem`) and `position: relative`; otherwise they grow forever.

## 10. Container queries (component adapts to its slot)
```css
.slot { container-type: inline-size; container-name: slot; }
.media { display: grid; gap: .75rem; }
@container slot (min-width: 30rem) { .media { grid-template-columns: 9rem 1fr; align-items: center; } }
@container slot (min-width: 48rem) { .media { grid-template-columns: 14rem 1fr auto; } }
```
Fallback: put a normal `@media (min-width: 640px)` rule before it; unsupported browsers keep the media rule.

## 11. Mobile bottom tab bar
```css
.tabbar { position: fixed; inset: auto 0 0 0; display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; background: var(--surface, #fff);
  border-top: 1px solid var(--border, #e5e7eb); padding-bottom: env(safe-area-inset-bottom); z-index: 200; }
.tabbar a { display: grid; justify-items: center; gap: 2px; padding: .5rem 0; min-height: 56px; font-size: .75rem; text-decoration: none; color: inherit; }
body.has-tabbar { padding-bottom: calc(56px + env(safe-area-inset-bottom)); }
@media (min-width: 768px) { .tabbar { display: none; } body.has-tabbar { padding-bottom: 0; } }
```

## 12. Breakpoints and helper tokens
```css
:root { --gutter: clamp(1rem, .5rem + 2vw, 2rem); --section-y: clamp(3rem, 2rem + 5vw, 7rem); --header-h: 4rem; }
/* 640 sm phones landscape | 768 md tablets | 1024 lg laptops | 1280 xl desktops | 1536 2xl */
.stack > * + * { margin-top: var(--stack, 1rem); }
.cluster { display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }
.switcher { display: flex; flex-wrap: wrap; gap: 1rem; } .switcher > * { flex: 1 1 calc((40rem - 100%) * 999); }
```
