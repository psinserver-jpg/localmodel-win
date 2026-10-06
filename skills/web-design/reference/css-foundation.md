---
name: css-foundation
description: Copy-paste CSS base for any site - modern reset, full light and dark token sheet, fluid type scale, container, layout utilities and grid recipes.
triggers: [css, stylesheet, style, tokens, design tokens, custom properties, variables, reset, dark mode, theme, grid, flexbox, layout, container, typography, font, spacing, 스타일, 다크모드, 테마, 레이아웃, 그리드, 폰트]
---
# CSS Foundation

Start every plain HTML/CSS project from this sheet. Paste it at the top of `<style>` (or `styles.css`) in this order: brief → tokens → reset → base → layout utilities → components. Change only token values to restyle the whole site.

## 1. Token sheet (light + dark + manual toggle)

The default palette below is "Slate Teal" (all text pairs pass WCAG AA). To change the look, replace the color values with a palette from `palettes-typography.md`; keep the token names.

```css
/* BRIEF purpose: ... | audience: ... | tone: ... | direction: ... | radius: 10px */
:root {
  color-scheme: light dark;

  /* Color: neutrals */
  --color-bg: #ffffff;
  --color-surface: #f4f6f8;       /* alternate sections, cards */
  --color-surface-2: #e9edf1;     /* hover rows, inset areas */
  --color-border: #dde3e9;        /* decorative dividers only */
  --color-border-strong: #7c8796; /* input borders: >= 3:1 on bg */
  --color-text: #0f172a;          /* 17.9:1 on bg */
  --color-text-muted: #475569;    /* 7.6:1 on bg, 7.0:1 on surface */
  /* Color: brand */
  --color-primary: #0f766e;       /* 5.5:1 on bg; links + primary buttons */
  --color-primary-hover: #115e59;
  --color-on-primary: #ffffff;    /* text on primary fill */
  --color-accent: #b45309;        /* 5.0:1; small highlights only */
  --color-focus: #0f766e;
  /* Color: status */
  --color-success: #15803d;
  --color-warning: #a16207;
  --color-danger: #b42318;

  /* Typography */
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-heading: var(--font-sans);
  --font-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
  /* Fluid scale: ~1.2 ratio at 360px -> ~1.25 at 1280px */
  --step--1: clamp(0.833rem, 0.81rem + 0.1vw, 0.9rem);
  --step-0: clamp(1rem, 0.95rem + 0.22vw, 1.125rem);
  --step-1: clamp(1.2rem, 1.1rem + 0.45vw, 1.41rem);
  --step-2: clamp(1.44rem, 1.27rem + 0.75vw, 1.76rem);
  --step-3: clamp(1.73rem, 1.45rem + 1.2vw, 2.2rem);
  --step-4: clamp(2.07rem, 1.6rem + 2vw, 2.75rem);
  --step-5: clamp(2.49rem, 1.75rem + 3.2vw, 3.44rem);
  --step-6: clamp(2.99rem, 1.9rem + 4.8vw, 4.3rem);
  --leading-tight: 1.15;
  --leading-snug: 1.3;
  --leading-body: 1.6;
  --measure: 65ch;

  /* Spacing: 4px base */
  --space-1: 0.25rem;  /* 4 */
  --space-2: 0.5rem;   /* 8 */
  --space-3: 0.75rem;  /* 12 */
  --space-4: 1rem;     /* 16 */
  --space-5: 1.5rem;   /* 24 */
  --space-6: 2rem;     /* 32 */
  --space-7: 3rem;     /* 48 */
  --space-8: 4rem;     /* 64 */
  --space-9: 6rem;     /* 96 */
  --space-10: 8rem;    /* 128 */
  --section-space: clamp(4rem, 3rem + 5vw, 8rem);
  --gutter: clamp(1rem, 0.5rem + 2.5vw, 2rem);
  --container: 72rem;      /* 1152px */
  --container-narrow: 45rem; /* 720px, articles */

  /* Shape and depth: pick ONE radius base and keep it */
  --radius-sm: 6px;
  --radius: 10px;
  --radius-lg: 16px;
  --radius-pill: 999px;
  --shadow-sm: 0 1px 2px rgb(15 23 42 / 0.06);
  --shadow-md: 0 1px 2px rgb(15 23 42 / 0.06), 0 4px 12px rgb(15 23 42 / 0.08);
  --shadow-lg: 0 2px 4px rgb(15 23 42 / 0.06), 0 12px 32px rgb(15 23 42 / 0.12);

  /* Motion */
  --ease: cubic-bezier(0.2, 0.7, 0.2, 1);
  --dur-fast: 150ms;
  --dur: 220ms;
  --dur-slow: 300ms;

  --header-h: 4rem;
}

/* Dark tokens: used by OS preference unless user forced light */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --color-bg: #0b1215;
    --color-surface: #121c20;
    --color-surface-2: #1a262b;
    --color-border: #233036;
    --color-border-strong: #6b7c86;
    --color-text: #e6edf0;
    --color-text-muted: #94a3b8;
    --color-primary: #2dd4bf;
    --color-primary-hover: #5eead4;
    --color-on-primary: #042f2e;
    --color-accent: #fbbf24;
    --color-focus: #5eead4;
    --color-success: #4ade80;
    --color-warning: #fbbf24;
    --color-danger: #f97066;
    --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.4);
    --shadow-md: 0 0 0 1px rgb(255 255 255 / 0.05), 0 4px 12px rgb(0 0 0 / 0.45);
    --shadow-lg: 0 0 0 1px rgb(255 255 255 / 0.06), 0 12px 32px rgb(0 0 0 / 0.55);
  }
}
/* Same dark values for a manual toggle: <html data-theme="dark"> */
:root[data-theme="dark"] {
  color-scheme: dark;
  --color-bg: #0b1215; --color-surface: #121c20; --color-surface-2: #1a262b;
  --color-border: #233036; --color-border-strong: #6b7c86;
  --color-text: #e6edf0; --color-text-muted: #94a3b8;
  --color-primary: #2dd4bf; --color-primary-hover: #5eead4; --color-on-primary: #042f2e;
  --color-accent: #fbbf24; --color-focus: #5eead4;
  --color-success: #4ade80; --color-warning: #fbbf24; --color-danger: #f97066;
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.4);
  --shadow-md: 0 0 0 1px rgb(255 255 255 / 0.05), 0 4px 12px rgb(0 0 0 / 0.45);
  --shadow-lg: 0 0 0 1px rgb(255 255 255 / 0.06), 0 12px 32px rgb(0 0 0 / 0.55);
}
:root[data-theme="light"] { color-scheme: light; }
```

Dark-mode rules: never just invert. Surfaces get lighter as they rise (bg < surface < surface-2). The primary gets lighter and the text on it gets dark. Shadows barely show on dark, so add a 1px light ring instead.

Optional theme toggle (works from `file://`; the `try` guards blocked storage):
```html
<button type="button" class="theme-toggle" aria-label="Toggle dark mode" aria-pressed="false">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
</button>
<script>
(() => {
  const root = document.documentElement;
  const btn = document.querySelector('.theme-toggle');
  let saved = null;
  try { saved = localStorage.getItem('theme'); } catch (e) {}
  if (saved) root.dataset.theme = saved;
  const isDark = () => root.dataset.theme
    ? root.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  if (!btn) return;
  btn.setAttribute('aria-pressed', String(isDark()));
  btn.addEventListener('click', () => {
    const next = isDark() ? 'light' : 'dark';
    root.dataset.theme = next;
    btn.setAttribute('aria-pressed', String(next === 'dark'));
    try { localStorage.setItem('theme', next); } catch (e) {}
  });
})();
</script>
```

## 2. Modern reset

```css
*, *::before, *::after { box-sizing: border-box; }
* { margin: 0; }
html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
@media (prefers-reduced-motion: no-preference) {
  html { scroll-behavior: smooth; }
}
body { min-height: 100svh; }
img, picture, video, canvas { display: block; max-width: 100%; height: auto; }
svg { max-width: 100%; flex-shrink: 0; }
input, button, textarea, select { font: inherit; color: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; }
textarea { resize: vertical; }
table { border-collapse: collapse; }
h1, h2, h3, h4, h5, h6, p, li, figcaption { overflow-wrap: break-word; }
ul[role="list"], ol[role="list"] { list-style: none; padding: 0; }
[hidden] { display: none !important; }
[id] { scroll-margin-top: calc(var(--header-h) + 1rem); } /* anchors clear the sticky header */
```

## 3. Base element styles

```css
body {
  font-family: var(--font-sans);
  font-size: var(--step-0);
  line-height: var(--leading-body);
  color: var(--color-text);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
h1, h2, h3, h4 {
  font-family: var(--font-heading);
  line-height: var(--leading-tight);
  letter-spacing: -0.02em;
  font-weight: 700;
  text-wrap: balance;
}
h1 { font-size: var(--step-6); }
h2 { font-size: var(--step-4); }
h3 { font-size: var(--step-2); line-height: var(--leading-snug); }
h4 { font-size: var(--step-1); line-height: var(--leading-snug); }
p { text-wrap: pretty; }
p { max-width: var(--measure); }
small, .text-sm { font-size: var(--step--1); }
a { color: var(--color-primary); text-underline-offset: 0.2em; text-decoration-thickness: 1px; }
a:hover { color: var(--color-primary-hover); text-decoration-thickness: 2px; }
strong { font-weight: 600; }
code, kbd, pre { font-family: var(--font-mono); font-size: 0.9em; }
pre { overflow-x: auto; padding: var(--space-4); background: var(--color-surface); border-radius: var(--radius); }
hr { border: 0; border-top: 1px solid var(--color-border); }
::selection { background: var(--color-primary); color: var(--color-on-primary); }

:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
  border-radius: 2px;
}

/* Korean: keep words intact, slightly looser lines, no negative tracking */
:lang(ko) body, body:lang(ko) {
  word-break: keep-all;
  overflow-wrap: anywhere;
  line-height: 1.7;
}
:lang(ko) h1, :lang(ko) h2, :lang(ko) h3 { letter-spacing: -0.01em; line-height: 1.25; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Korean font setup (put in `<head>` before your stylesheet), then set `--font-sans`:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
```
```css
:root { --font-sans: "Pretendard Variable", Pretendard, system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif; }
```
Latin fonts from Google Fonts (always add the preconnects and `display=swap`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
```

## 4. Layout utilities

```css
/* Skip link: first element inside <body> */
.skip-link {
  position: absolute; left: var(--space-4); top: -100%;
  padding: var(--space-2) var(--space-4);
  background: var(--color-text); color: var(--color-bg);
  border-radius: var(--radius-sm); z-index: 1000;
}
.skip-link:focus { top: var(--space-4); }

/* Screen-reader-only text */
.visually-hidden {
  position: absolute !important; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

/* Centered content column with side gutters */
.container {
  width: min(100% - 2 * var(--gutter), var(--container));
  margin-inline: auto;
}
.container--narrow { width: min(100% - 2 * var(--gutter), var(--container-narrow)); }

/* Vertical rhythm for sections */
.section { padding-block: var(--section-space); }
.section--alt { background: var(--color-surface); }
.section__head { max-width: 40rem; margin-bottom: var(--space-7); }
.section__head--center { margin-inline: auto; text-align: center; }
.section__head--center p { margin-inline: auto; }

/* Stack: even vertical spacing between children */
.stack > * + * { margin-top: var(--stack-space, var(--space-4)); }
.stack-lg { --stack-space: var(--space-6); }

/* Cluster: wrapping horizontal group (buttons, tags, nav) */
.cluster { display: flex; flex-wrap: wrap; gap: var(--cluster-gap, var(--space-3)); align-items: center; }

/* Text helpers */
.eyebrow {
  font-size: var(--step--1); font-weight: 600; color: var(--color-primary);
  text-transform: uppercase; letter-spacing: 0.08em;
}
:lang(ko) .eyebrow { text-transform: none; letter-spacing: 0.02em; }
.lead { font-size: var(--step-1); color: var(--color-text-muted); line-height: 1.5; }
.muted { color: var(--color-text-muted); }
.center { text-align: center; }
```

## 5. Grid recipes

**Auto-fit card grid** (1 column on phones, as many 16rem columns as fit; no media query):
```css
.grid-auto {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, var(--min, 16rem)), 1fr));
  gap: var(--space-5);
}
.grid-auto > * { min-width: 0; }
```
Use `style="--min: 20rem"` for wider cards. Prefer `auto-fill` when there may be only 1–2 items (keeps card width stable).

**Fixed 2/3/4 columns, mobile-first:**
```css
.grid { display: grid; gap: var(--space-5); }
@media (min-width: 640px)  { .grid--2, .grid--3, .grid--4 { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .grid--3 { grid-template-columns: repeat(3, 1fr); }
                             .grid--4 { grid-template-columns: repeat(4, 1fr); } }
```

**Split (text + media), stacks on mobile:**
```css
.split { display: grid; gap: var(--space-7); align-items: center; }
@media (min-width: 900px) {
  .split { grid-template-columns: 1fr 1fr; }
  .split--wide-text { grid-template-columns: 1.2fr 1fr; }
  .split--reverse > :first-child { order: 2; }
}
```

**Sidebar + content** (sidebar wraps under content when space < 40rem, no media query):
```css
.with-sidebar { display: flex; flex-wrap: wrap; gap: var(--space-6); }
.with-sidebar > .sidebar { flex: 1 1 16rem; }
.with-sidebar > .content { flex: 999 1 0; min-width: min(100%, 40rem); }
```

**Sticky footer page shell:**
```css
body { display: grid; grid-template-rows: auto 1fr auto; min-height: 100svh; }
```

**Bento grid** (featured tiles of mixed size, collapses to 1 column):
```css
.bento { display: grid; gap: var(--space-4); grid-template-columns: 1fr; }
@media (min-width: 768px) {
  .bento { grid-template-columns: repeat(4, 1fr); grid-auto-rows: minmax(11rem, auto); }
  .bento .tile--lg   { grid-column: span 2; grid-row: span 2; }
  .bento .tile--wide { grid-column: span 2; }
}
.bento .tile { background: var(--color-surface); border-radius: var(--radius-lg); padding: var(--space-5); }
```

**Container-query card** (card adapts to its own width, not the viewport):
```css
.card-wrap { container-type: inline-size; }
.media-card { display: grid; gap: var(--space-4); }
@container (min-width: 32rem) {
  .media-card { grid-template-columns: 12rem 1fr; align-items: center; }
}
```

**Full-bleed band inside a container layout:**
```css
.full-bleed { width: 100%; } /* put the band OUTSIDE .container, and a .container inside it */
```
Never use `width: 100vw` (it includes the scrollbar and causes horizontal scroll on Windows).

## 6. Surface patterns

```css
.card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}
.section--alt .card { background: var(--color-bg); } /* cards pop on tinted sections */

/* Soft hero glow: one radial gradient, low contrast */
.glow {
  background:
    radial-gradient(60rem 30rem at 85% -10%, color-mix(in srgb, var(--color-primary) 14%, transparent), transparent 70%),
    var(--color-bg);
}

/* Subtle dot pattern (no image file needed) */
.dots {
  background-image: radial-gradient(color-mix(in srgb, var(--color-text) 12%, transparent) 1px, transparent 1px);
  background-size: 20px 20px;
}

/* Responsive table wrapper */
.table-wrap { overflow-x: auto; border: 1px solid var(--color-border); border-radius: var(--radius); }
.table-wrap table { width: 100%; min-width: 36rem; }
.table-wrap th, .table-wrap td { padding: var(--space-3) var(--space-4); text-align: left; border-bottom: 1px solid var(--color-border); }
.table-wrap th { font-size: var(--step--1); color: var(--color-text-muted); font-weight: 600; background: var(--color-surface); }
.table-wrap td.num { text-align: right; font-variant-numeric: tabular-nums; }
```

## 7. Rules for using this sheet
- Do not add new colors in components; if you need a tint, use `color-mix(in srgb, var(--color-primary) 12%, var(--color-bg))`.
- Only `--step-*` sizes for text; only `--space-*` for margin, padding and gap.
- Use the same `--radius` for buttons and inputs; `--radius-lg` for cards and images; `--radius-pill` for tags and avatars.
- Keep `p { max-width: var(--measure) }`; override with `max-width: none` inside cards/tables if needed.
- Section order of CSS: tokens, reset, base, utilities, components (header, hero, buttons, cards...), page-specific, media queries last within each component block.
