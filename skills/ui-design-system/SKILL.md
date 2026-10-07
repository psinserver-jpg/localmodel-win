---
name: ui-design-system
description: Build a consistent UI design system with CSS variable tokens (color, space, radius, shadow, z-index, type) and fully-stated components (buttons, inputs, cards, modals, toasts, tables, tabs, badges) with light/dark themes. Use for design tokens, component styling, UI kits and consistent-looking interfaces.
triggers: [design system, design token, design tokens, ui kit, component library, style guide, css variables, custom properties, button styles, input styles, form styles, card component, modal, dialog, toast, notification, snackbar, table style, tabs, badge, chip, tag, elevation, shadow scale, spacing scale, theme, theming, light dark, dark theme, focus ring, hover state, disabled state, loading state, empty state, skeleton, 디자인 시스템, 디자인 토큰, 컴포넌트, 컴포넌트 라이브러리, 스타일 가이드, 버튼 스타일, 입력창, 입력 폼, 카드, 모달, 토스트, 알림, 테이블, 표 스타일, 탭, 뱃지, 배지, 그림자, 간격, 테마, 라이트 다크, 다크 테마, 포커스, 호버, 비활성, 로딩 상태, 빈 상태, 에러 상태, ui 통일, 일관된 디자인]
priority: 48
---
# UI Design System

Goal: every screen looks like one product. Define tokens ONCE in `:root`; components use only tokens (no raw hex/px below the token block).

## Hard rules
1. Tokens first, components second. Categories: `--bg --surface --surface-2 --border --text --text-muted --primary --primary-hover --on-primary --danger --success --warning`, `--space-1..12`, `--radius-sm/md/lg/full`, `--shadow-1..3`, `--z-*`, `--font-*`, `--fs-*`.
2. Spacing scale (4px base): 4, 8, 12, 16, 24, 32, 48, 64 = `--space-1,2,3,4,6,8,12,16` (rem: .25 .5 .75 1 1.5 2 3 4). Never 13px/22px.
3. ONE radius family: 6px controls, 12px cards, 16-20px modals, 999px pills. Do not mix sharp and round.
4. Elevation = shadow + surface. Max 3 levels: 1 card, 2 dropdown/popover, 3 modal. Dark mode: lighter surface instead of heavier shadow.
5. Every interactive component MUST define all states: default, hover, `:focus-visible`, active, disabled, loading, error (inputs), empty (lists/tables).
   - hover: bg shifts ~8% (use `color-mix(in srgb, var(--primary) 88%, black)`), `cursor: pointer`.
   - focus-visible: `outline: 2px solid var(--primary); outline-offset: 2px` (3:1 against bg). Never `outline: none` without a replacement.
   - active: `transform: translateY(1px)`; disabled: `opacity: .5; cursor: not-allowed; pointer-events: none` + `disabled` attribute.
   - loading: `aria-busy="true"`, spinner, keep width, block clicks.
   - error: red border + message under field with `aria-describedby` and `aria-invalid="true"`; never color alone (add icon/text).
6. Touch targets >= 44x44px (`min-height: 44px`). Inputs font-size >= 16px (prevents iOS zoom).
7. Theming: light = `:root`, dark = `@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]) {...} }` AND `:root[data-theme="dark"]{...}`. Add `color-scheme: light dark`. Dark bg `#0f1115` (not black), text `#e6e8ec`, lighten primary until contrast >= 4.5:1.
8. z-index scale only: dropdown 100, sticky 200, overlay 300, modal 400, toast 500. No `z-index: 9999`.
9. Density: default control 44px; compact 36px for tables/admin via `[data-density="compact"]`.
10. Korean UI: font `"Pretendard Variable", Pretendard, "Noto Sans KR", system-ui, sans-serif`; `word-break: keep-all`; button text short (저장, 취소, 다음); errors polite and specific ("이메일 형식이 올바르지 않아요").
11. Use native elements: `<button>`, `<dialog>` (showModal), `<input>` + `<label for>`, `<table>`. Toasts: container with `role="status" aria-live="polite"`.
12. Output as ONE index.html (style + body + script) unless asked otherwise. Tailwind: reuse the vars via `bg-[var(--surface)]`.

## Minimal token core (copy, then extend from reference/tokens-and-base.md)
```css
:root {
  color-scheme: light dark;
  --bg: #f8f9fb; --surface: #ffffff; --surface-2: #f1f3f6; --border: #dde1e7;
  --text: #14171c; --text-muted: #5b6472;
  --primary: #2563eb; --primary-hover: #1d4ed8; --on-primary: #ffffff;
  --danger: #c62828; --success: #15803d; --warning: #b45309;
  --space-1: .25rem; --space-2: .5rem; --space-3: .75rem; --space-4: 1rem; --space-6: 1.5rem; --space-8: 2rem;
  --radius-sm: 6px; --radius-md: 12px; --radius-lg: 20px; --radius-full: 999px;
  --shadow-1: 0 1px 2px rgb(16 24 40 / .06), 0 1px 3px rgb(16 24 40 / .10);
  --shadow-2: 0 4px 8px -2px rgb(16 24 40 / .10), 0 2px 4px -2px rgb(16 24 40 / .06);
  --shadow-3: 0 20px 40px -12px rgb(16 24 40 / .25);
  --font: "Pretendard Variable", Pretendard, "Noto Sans KR", system-ui, -apple-system, "Segoe UI", sans-serif;
  --ease: cubic-bezier(.2, 0, 0, 1); --dur: 160ms;
}
:root[data-theme="dark"] {
  --bg: #0f1115; --surface: #171a21; --surface-2: #1f232c; --border: #2b303b;
  --text: #e6e8ec; --text-muted: #9aa3b2;
  --primary: #6ea8fe; --primary-hover: #8dbaff; --on-primary: #0b1220;
  --danger: #ff8a80; --success: #5fd38a; --warning: #f5b94a;
}
body { margin: 0; background: var(--bg); color: var(--text); font: 400 1rem/1.6 var(--font); word-break: keep-all; }
.btn { min-height: 44px; padding: 0 var(--space-4); border: 1px solid transparent; border-radius: var(--radius-sm);
  font: 600 1rem var(--font); cursor: pointer; background: var(--primary); color: var(--on-primary);
  transition: background var(--dur) var(--ease), transform var(--dur) var(--ease); }
.btn:hover { background: var(--primary-hover); }
.btn:active { transform: translateY(1px); }
.btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn--ghost { background: transparent; color: var(--text); border-color: var(--border); }
.btn--ghost:hover { background: var(--surface-2); }
```
Theme toggle (persist safely):
```html
<button class="btn btn--ghost" id="themeBtn" type="button">테마 바꾸기</button>
<script>
const root = document.documentElement;
try { const t = localStorage.getItem('theme'); if (t) root.dataset.theme = t; } catch (e) {}
document.getElementById('themeBtn').addEventListener('click', () => {
  const dark = root.dataset.theme === 'dark' || (!root.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
  root.dataset.theme = dark ? 'light' : 'dark';
  try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
});
</script>
```

## Pitfalls
- Hardcoded `#fff`/`#000` inside components breaks dark mode: always `var(--surface)` / `var(--text)`.
- Dark-theme tokens defined only in media query: manual toggle then fails. Define both.
- White text on `#3b82f6`/green `#10b981` fails AA; use `#2563eb`, `#047857`.
- Cards: border OR shadow, not both heavy. Padding 16-24px.
- Modal: use `<dialog>`, close on Esc/backdrop, focus returns to opener, `overscroll-behavior: contain`.
- Table: sticky header, right-align numbers with `font-variant-numeric: tabular-nums`, wrap in `overflow-x: auto`, show an empty row message.
- Deep recipes (inputs, modal, toast, table, tabs, badges, states): see reference files.
