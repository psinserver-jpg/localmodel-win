---
name: tokens-and-base
description: Complete paste-ready token stylesheet (color, space, radius, shadow, z-index, type, density) with light and dark themes, reset, and base typography.
triggers: [design tokens, css variables, token stylesheet, base css, reset, theme, dark theme, light dark, spacing scale, z-index, shadow scale, 디자인 토큰, 테마, 다크 테마, 기본 스타일, 리셋, 간격, 그림자]
---
# Token + base stylesheet

Paste into `<style>` first. Everything after uses `var(--...)` only.

```css
:root {
  color-scheme: light dark;
  /* color: neutrals */
  --bg: #f8f9fb;  --surface: #ffffff;  --surface-2: #f1f3f6;  --surface-3: #e6e9ee;
  --border: #dde1e7;  --border-strong: #b8bfca;
  --text: #14171c;  --text-muted: #5b6472;  --text-faint: #737d8c;
  /* color: brand + status (each has a soft tint for badges/alerts) */
  --primary: #2563eb;  --primary-hover: #1d4ed8;  --primary-soft: #e8efff;  --on-primary: #ffffff;
  --danger: #c62828;   --danger-soft: #fdeaea;
  --success: #15803d;  --success-soft: #e4f6ea;
  --warning: #b45309;  --warning-soft: #fdf1dc;
  --info: #0369a1;     --info-soft: #e2f2fb;
  --overlay: rgb(10 14 22 / .55);
  /* space: 4px base */
  --space-1: .25rem; --space-2: .5rem; --space-3: .75rem; --space-4: 1rem; --space-5: 1.25rem;
  --space-6: 1.5rem; --space-8: 2rem; --space-12: 3rem; --space-16: 4rem; --space-24: 6rem;
  /* radius */
  --radius-sm: 6px; --radius-md: 12px; --radius-lg: 20px; --radius-full: 999px;
  /* elevation */
  --shadow-1: 0 1px 2px rgb(16 24 40 / .06), 0 1px 3px rgb(16 24 40 / .10);
  --shadow-2: 0 4px 8px -2px rgb(16 24 40 / .10), 0 2px 4px -2px rgb(16 24 40 / .06);
  --shadow-3: 0 20px 40px -12px rgb(16 24 40 / .25);
  --ring: 0 0 0 3px color-mix(in srgb, var(--primary) 30%, transparent);
  /* z-index */
  --z-dropdown: 100; --z-sticky: 200; --z-overlay: 300; --z-modal: 400; --z-toast: 500;
  /* type */
  --font: "Pretendard Variable", Pretendard, "Noto Sans KR", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: ui-monospace, "SF Mono", "JetBrains Mono", Consolas, monospace;
  --fs-sm: .875rem; --fs-base: 1rem; --fs-lg: 1.125rem; --fs-xl: 1.375rem; --fs-2xl: 1.75rem; --fs-3xl: clamp(2rem, 1.4rem + 2.4vw, 3rem);
  /* control sizing (density) */
  --control-h: 44px; --control-px: var(--space-4);
  /* motion */
  --ease: cubic-bezier(.2, 0, 0, 1); --dur-fast: 120ms; --dur: 200ms; --dur-slow: 320ms;
}
[data-density="compact"] { --control-h: 36px; --control-px: var(--space-3); --fs-base: .9375rem; }

/* dark: follows the OS unless the user forced light */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1115; --surface: #171a21; --surface-2: #1f232c; --surface-3: #2a2f3a;
    --border: #2b303b; --border-strong: #444b5a;
    --text: #e6e8ec; --text-muted: #9aa3b2; --text-faint: #7d8696;
    --primary: #6ea8fe; --primary-hover: #8dbaff; --primary-soft: #1b2a45; --on-primary: #0b1220;
    --danger: #ff8a80; --danger-soft: #3a1c1e; --success: #5fd38a; --success-soft: #16301f;
    --warning: #f5b94a; --warning-soft: #372a12; --info: #6cc4f0; --info-soft: #13293a;
    --overlay: rgb(0 0 0 / .65);
    --shadow-1: 0 1px 2px rgb(0 0 0 / .4); --shadow-2: 0 6px 14px -4px rgb(0 0 0 / .5); --shadow-3: 0 24px 48px -12px rgb(0 0 0 / .7);
  }
}
/* dark: forced via data-theme="dark" (same values) */
:root[data-theme="dark"] {
  --bg: #0f1115; --surface: #171a21; --surface-2: #1f232c; --surface-3: #2a2f3a;
  --border: #2b303b; --border-strong: #444b5a;
  --text: #e6e8ec; --text-muted: #9aa3b2; --text-faint: #7d8696;
  --primary: #6ea8fe; --primary-hover: #8dbaff; --primary-soft: #1b2a45; --on-primary: #0b1220;
  --danger: #ff8a80; --danger-soft: #3a1c1e; --success: #5fd38a; --success-soft: #16301f;
  --warning: #f5b94a; --warning-soft: #372a12; --info: #6cc4f0; --info-soft: #13293a;
  --overlay: rgb(0 0 0 / .65);
  --shadow-1: 0 1px 2px rgb(0 0 0 / .4); --shadow-2: 0 6px 14px -4px rgb(0 0 0 / .5); --shadow-3: 0 24px 48px -12px rgb(0 0 0 / .7);
}

*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 400 var(--fs-base)/1.65 var(--font);
  word-break: keep-all; overflow-wrap: anywhere;
  -webkit-font-smoothing: antialiased;
}
img, svg, video { max-width: 100%; height: auto; display: block; }
h1, h2, h3 { line-height: 1.25; letter-spacing: -.01em; text-wrap: balance; margin: 0 0 var(--space-3); }
p { margin: 0 0 var(--space-4); text-wrap: pretty; max-width: 68ch; }
a { color: var(--primary); text-underline-offset: .2em; }
:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
:where(button, input, select, textarea) { font: inherit; color: inherit; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.container { width: min(100% - 2rem, 72rem); margin-inline: auto; }
.stack > * + * { margin-top: var(--space-4); }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-6); box-shadow: var(--shadow-1); }
.card--interactive { transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease); }
.card--interactive:hover { transform: translateY(-2px); box-shadow: var(--shadow-2); }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; scroll-behavior: auto !important; } }
```

## Contrast check of the pairs above
- `--text` on `--bg` light: 16:1. `--text-muted` `#5b6472` on `#fff`: 6:1 (AA). `--text-faint` `#737d8c` on `#fff`: 4.0:1 -> only for large text/decoration, never body.
- `--on-primary` white on `#2563eb`: 5.2:1. Dark: `#0b1220` on `#6ea8fe`: 8:1.
- Fallback without `color-mix()`: replace `--ring` with `0 0 0 3px rgb(37 99 235 / .3)`.

## Tailwind notes
Keep the same vars and map them in config: `colors: { surface: 'var(--surface)', primary: 'var(--primary)' }`. Toggle dark by `document.documentElement.dataset.theme`.
