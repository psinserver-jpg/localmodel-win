---
name: type-scale-pairing
description: Fluid modular type scale tokens, Korean-friendly font stacks and pairings, article/heading/label/number styles, line length and leading tables, and a scale calculator.
triggers: [type scale, font pairing, font stack, fluid typography, clamp, heading size, line height, letter spacing, line length, readability, korean font, pretendard, noto sans kr, noto serif kr, tabular numbers, 폰트, 글꼴, 타이포그래피, 글자 크기, 행간, 자간, 가독성, 한글 폰트, 프리텐다드, 폰트 조합]
---
# Type scale and pairing

## Fluid scale (ratio about 1.25 on phones, 1.333 on desktop)
```css
:root {
  --fs--1: clamp(.8rem, .78rem + .1vw, .875rem);
  --fs-0:  clamp(1rem, .96rem + .2vw, 1.125rem);
  --fs-1:  clamp(1.2rem, 1.1rem + .5vw, 1.45rem);
  --fs-2:  clamp(1.44rem, 1.25rem + .95vw, 1.92rem);
  --fs-3:  clamp(1.73rem, 1.4rem + 1.65vw, 2.56rem);
  --fs-4:  clamp(2.07rem, 1.5rem + 2.85vw, 3.41rem);
  --fs-5:  clamp(2.49rem, 1.5rem + 4.95vw, 4.55rem);
  --lh-body: 1.65; --lh-body-ko: 1.75; --lh-heading: 1.2; --lh-display: 1.08;
  --font-sans: "Pretendard Variable", Pretendard, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  --font-serif: "Noto Serif KR", "Nanum Myeongjo", "Iowan Old Style", Georgia, serif;
  --font-mono: ui-monospace, "SF Mono", "D2Coding", Consolas, monospace;
}
html { font-family: var(--font-sans); font-size: 100%; }
html:lang(ko) body { line-height: var(--lh-body-ko); word-break: keep-all; overflow-wrap: anywhere; }
body { font-size: var(--fs-0); line-height: var(--lh-body); }
h1 { font-size: var(--fs-5); line-height: var(--lh-display); letter-spacing: -.025em; font-weight: 800; }
h2 { font-size: var(--fs-4); line-height: 1.15; letter-spacing: -.02em; font-weight: 700; }
h3 { font-size: var(--fs-2); line-height: var(--lh-heading); letter-spacing: -.01em; font-weight: 700; }
h4 { font-size: var(--fs-1); line-height: 1.3; font-weight: 600; }
:where(h1, h2, h3, h4) { text-wrap: balance; margin-block: 0 .5em; }
:lang(ko) :where(h1, h2, h3) { letter-spacing: -.01em; }
small, .caption { font-size: var(--fs--1); line-height: 1.5; }
```

## Roles (specs to copy)
| Role | size | weight | leading | tracking | other |
|---|---|---|---|---|---|
| Display / hero h1 | --fs-5 | 800 | 1.08 | -.025em (ko -.01em) | max 14-18 ch wide per line group |
| Section h2 | --fs-4 | 700 | 1.15 | -.02em | |
| Card title h3 | --fs-2 | 700 | 1.2 | -.01em | |
| Lead paragraph | --fs-1 | 400 | 1.55 | 0 | muted color, max 60ch |
| Body | --fs-0 | 400 | 1.65 (ko 1.75) | 0 | 65ch (ko about 40 chars) |
| UI label / button | .9375rem | 600 | 1.25 | 0 | never wraps: `white-space: nowrap` |
| Eyebrow | .8125rem | 700 | 1.2 | .08em | uppercase for Latin only |
| Caption / meta | .8125rem | 400 | 1.5 | .01em | muted |
| Code | .9em | 400 | 1.6 | 0 | mono, `tab-size: 2` |
| Numbers / KPI | --fs-4 | 700 | 1 | -.02em | `tabular-nums` |

## Pairings that work (max 2)
| Mood | Heading | Body | Load |
|---|---|---|---|
| Neutral modern (default) | Pretendard 700-800 | Pretendard 400 | jsDelivr Pretendard Variable |
| Editorial / magazine | Noto Serif KR 700 | Pretendard 400 | Google Fonts `family=Noto+Serif+KR:wght@600;700` |
| Friendly / startup | Pretendard 800 | Pretendard 400 | same |
| Technical / dev tool | Inter 700 + JetBrains Mono accents | Inter 400 | Google Fonts `Inter:wght@400;600;700` and `JetBrains+Mono:wght@400;600` |
| Premium / luxury | "Playfair Display" 600 (Latin) + Noto Serif KR | Pretendard 300-400 | Google Fonts |
| Playful | "Jua" or "Gmarket Sans" headings only | Pretendard | Jua from Google Fonts |

Google Fonts link (Noto Sans KR + Serif):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Noto+Serif+KR:wght@600;700&display=swap">
```
Fallback behavior: if the CDN is blocked, the stack falls to Apple SD Gothic Neo / Malgun Gothic, so layout stays sane. Never rely on a font being installed locally.

## Article page
```css
.prose { max-width: 42rem; margin-inline: auto; font-size: 1.0625rem; line-height: 1.8; }
.prose :where(p, ul, ol) { margin-block: 0 1.25em; }
.prose h2 { margin-top: 2.2em; }
.prose blockquote { margin: 1.5em 0; padding-left: 1.25rem; border-left: 3px solid var(--primary); color: var(--text-muted); font-family: var(--font-serif); }
.prose :where(code) { font-family: var(--font-mono); background: var(--surface-2); padding: .1em .35em; border-radius: 4px; font-size: .9em; }
.prose > p:first-of-type::first-line { font-weight: 600; }
```

## Number and price styling
```css
.kpi { font-size: var(--fs-4); font-weight: 700; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.price del { color: var(--text-muted); font-weight: 400; }
.price ins { text-decoration: none; font-weight: 800; }
```
```js
const won = (n) => n.toLocaleString('ko-KR') + '원';
const compact = (n) => new Intl.NumberFormat('ko-KR', { notation: 'compact' }).format(n);
console.log(won(38000), compact(1250000)); // 38,000원 125만
```

## Scale calculator (when you need a custom ratio)
```js
function typeScale(base = 16, ratio = 1.25, up = 5, down = 1) {
  const out = {};
  for (let i = -down; i <= up; i++) out['step' + i] = +(base * ratio ** i / 16).toFixed(3) + 'rem';
  return out;
}
console.log(typeScale(16, 1.25));
```
Common ratios: 1.125 dense UI, 1.2 minor third, 1.25 major third (default), 1.333 perfect fourth (marketing), 1.5 dramatic.

## Pitfalls
- Hangul needs more leading than Latin; 1.5 looks cramped, 1.7-1.8 is right.
- Do not use `letter-spacing` below -.03em, Hangul glyphs collide.
- Mixing Hangul + Latin in one heading: Pretendard and Inter metrics match; with Noto Serif KR Latin glyphs come from the same face, fine.
- `font-weight: 300` Korean at small size is hard to read; use 400+ below 18px.
- Avoid italic Korean (synthesized slant looks broken); use weight or color for emphasis.
- Text in images and fixed `px` sizes break zoom; always rem.
