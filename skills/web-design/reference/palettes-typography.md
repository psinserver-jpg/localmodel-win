---
name: palettes-typography
description: Ready-made named color palettes with light and dark values that pass contrast, plus font pairings including Korean fonts.
triggers: [color, colour, palette, theme, dark mode, font, typography, typeface, brand, 색상, 컬러, 팔레트, 테마, 다크모드, 폰트, 글꼴, 타이포, 브랜드]
---
# Palettes & Typography

Pick ONE palette that fits the tone, copy its tokens into `:root`, and never add extra random colors. Each palette: background, surface, text, muted text, border, primary (+ text on primary), accent. Text/muted values pass 4.5:1 on their background; primary buttons pass 4.5:1 with their on-primary text.

## Token template

```css
:root {
  --color-bg: #ffffff; --color-surface: #f8fafc; --color-text: #0f172a; --color-muted: #475569;
  --color-border: #e2e8f0; --color-primary: #2563eb; --color-on-primary: #ffffff; --color-accent: #f59e0b;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root { --color-bg: #0b1120; --color-surface: #111827; --color-text: #e5e7eb; --color-muted: #9ca3af;
    --color-border: #1f2937; --color-primary: #60a5fa; --color-on-primary: #0b1120; --color-accent: #fbbf24; }
}
```

## Palettes (light / dark)

| Name & mood | bg | surface | text | muted | border | primary / on | accent |
|---|---|---|---|---|---|---|---|
| **Trust Blue** — SaaS, finance, corporate | `#ffffff` / `#0b1120` | `#f8fafc` / `#111827` | `#0f172a` / `#e5e7eb` | `#475569` / `#9ca3af` | `#e2e8f0` / `#1f2937` | `#2563eb`+`#fff` / `#60a5fa`+`#0b1120` | `#f59e0b` / `#fbbf24` |
| **Forest** — eco, wellness, outdoor | `#fbfaf7` / `#0f1712` | `#f1efe8` / `#16211a` | `#1c2a21` / `#e4ebe5` | `#4b5d52` / `#9fb2a5` | `#dcdfd5` / `#24332a` | `#166534`+`#fff` / `#4ade80`+`#0f1712` | `#b45309` / `#f59e0b` |
| **Warm Café** — restaurant, bakery, local shop | `#fffaf3` / `#1a1410` | `#f6ede0` / `#231b15` | `#2b1d12` / `#f1e7dc` | `#6b5444` / `#b8a493` | `#e8dccb` / `#33281f` | `#9a3412`+`#fff` / `#fb923c`+`#1a1410` | `#4d7c0f` / `#a3e635` |
| **Midnight Neon** — tech, gaming, launch page | `#f8fafc` / `#05060a` | `#eef2f7` / `#0d1017` | `#0b1020` / `#e6e9f2` | `#4a5368` / `#9aa3b8` | `#dde3ec` / `#1a1f2b` | `#6d28d9`+`#fff` / `#a78bfa`+`#05060a` | `#0891b2` / `#22d3ee` |
| **Mono Editorial** — portfolio, blog, agency | `#ffffff` / `#0a0a0a` | `#f5f5f4` / `#171717` | `#111111` / `#ededed` | `#57534e` / `#a3a3a3` | `#e7e5e4` / `#262626` | `#111111`+`#fff` / `#ededed`+`#0a0a0a` | `#dc2626` / `#f87171` |
| **Coral Pop** — kids, events, consumer app | `#fffdfb` / `#160f10` | `#fff1ec` / `#21171a` | `#2a1215` / `#f5e6e8` | `#6b4a4f` / `#c2a3a8` | `#f3dcd6` / `#33242a` | `#be123c`+`#fff` / `#fb7185`+`#160f10` | `#0f766e` / `#2dd4bf` |
| **Medical Teal** — clinic, health, education | `#ffffff` / `#071413` | `#f0f9f8` / `#0e1f1e` | `#0b2524` / `#e0efed` | `#3f5f5d` / `#93b3b0` | `#d5e8e6` / `#1a3230` | `#0f766e`+`#fff` / `#2dd4bf`+`#071413` | `#7c3aed` / `#a78bfa` |
| **Luxury Gold** — hotel, jewelry, premium | `#fbfaf8` / `#0c0b09` | `#f2efe9` / `#16140f` | `#1a1712` / `#ece6da` | `#5e574a` / `#aaa18e` | `#e3ddd1` / `#29251c` | `#1a1712`+`#fbfaf8` / `#d4b06a`+`#0c0b09` | `#8a6d2f` / `#d4b06a` |
| **Sky Startup** — productivity, AI tool | `#ffffff` / `#0a0f1c` | `#f5f8ff` / `#121a2e` | `#101828` / `#e4e9f5` | `#475467` / `#98a2b3` | `#e4e7ec` / `#1f2a44` | `#4338ca`+`#fff` / `#818cf8`+`#0a0f1c` | `#0ea5e9` / `#38bdf8` |
| **Earth Clay** — architecture, interior, craft | `#faf7f2` / `#14110e` | `#efe8dd` / `#1d1915` | `#2a231c` / `#ece4d8` | `#665a4c` / `#b0a291` | `#e0d6c7` / `#2e2821` | `#7c2d12`+`#fff` / `#ea8a5c`+`#14110e` | `#3f6212` / `#a3c45a` |

Rules:
- 60% bg/surface, 30% text/neutral, 10% primary + accent. Accent is for small highlights only (badges, underline, one icon), never large text on white unless it passes 4.5:1.
- Use `--color-primary` for exactly one kind of main action. Secondary buttons: transparent background + border.
- Gradients: two adjacent hues of the same palette at low contrast, e.g. `linear-gradient(135deg, var(--color-surface), var(--color-bg))`. Avoid purple→blue rainbow gradients on everything.

## Font pairings

Load at most 2 families, 2–3 weights each. Always end stacks with system fonts.

| Mood | Headings | Body | Notes |
|---|---|---|---|
| Clean Korean (default) | Pretendard 700 | Pretendard 400 | Best general Korean UI font |
| Korean editorial | Noto Serif KR 700 | Pretendard 400 | Magazine, essay, culture |
| Friendly Korean | Gmarket Sans / Pretendard 800 | Pretendard 400 | Events, kids, food |
| Modern SaaS (EN) | Inter 700 | Inter 400 | Neutral, readable |
| Elegant (EN) | Playfair Display 700 | Source Sans 3 400 | Luxury, restaurant |
| Tech (EN) | Space Grotesk 700 | Inter 400 | Startup, developer |
| Editorial (EN) | Fraunces 700 | Inter 400 | Blog, portfolio |
| Code / dashboard | Inter 600 | Inter 400 + JetBrains Mono for numbers/code | Use `font-variant-numeric: tabular-nums` |

### Loading

```html
<!-- Pretendard (Korean + Latin) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
<!-- Google Fonts example: Noto Sans KR + Inter -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
```

```css
:root {
  --font-sans: "Pretendard", "Noto Sans KR", system-ui, -apple-system, "Segoe UI", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
  --font-serif: "Noto Serif KR", Georgia, "Times New Roman", serif;
  --font-mono: "JetBrains Mono", ui-monospace, "Cascadia Code", Consolas, monospace;
}
body { font-family: var(--font-sans); line-height: 1.6; }
:lang(ko) { word-break: keep-all; overflow-wrap: anywhere; }
h1, h2, h3 { line-height: 1.2; letter-spacing: -0.02em; }
```

- Korean body line-height 1.6–1.8 (taller than Latin). Headings 1.2–1.3.
- Negative letter-spacing only on large headings (−0.01 to −0.03em), never on body text.
- Weights: body 400, emphasis 600, headings 700. Avoid 300 for Korean body text on screens (too thin).
- Works offline / no CDN: the system stack above still looks good on Windows (Malgun Gothic) and macOS (Apple SD Gothic Neo).
