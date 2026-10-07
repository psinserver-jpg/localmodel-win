---
name: brand-guide
description: Brand mini-guide template (palette, type, spacing, logo rules, tone of voice), light and dark logo variants, social avatar and Open Graph card as SVG, favicon export checklist.
triggers: [brand guide, style guide, brand palette, brand colors, typography, tone of voice, logo variants, dark logo, social avatar, profile image, open graph, og image, brand kit, favicon, 브랜드 가이드, 스타일 가이드, 브랜드 컬러, 톤앤매너, 로고 변형, 다크 로고, 소셜 아바타, 프로필 이미지, 브랜드 키트]
---
# Brand mini-guide

Deliver as one HTML page (sections: Logo, Color, Type, Spacing, Voice). Fill with the REAL brand; example is cafe "모닝브루".

## Guide content template
- Logo: primary lockup, icon-only, one-color, dark version; clear space = height of the cup glyph; minimum size 24px icon / 96px lockup; do-nots (stretch, recolor, add shadow, busy backgrounds).
- Color tokens (name, hex, role, contrast): `--brand #7c4a2d` primary (white text 7.3:1), `--accent #e4572e` highlight (use for buttons with white text 4.0:1, so bold 18px+ only), `--cream #fff4e0` background, `--ink #2b1d14` text (13:1 on cream), `--line #e8d9c5`. Ratio 60% cream / 30% brand / 10% accent.
- Type: Heading Pretendard 800 (or Black Han Sans for playful), body Pretendard 400/500 16px/1.7, `word-break: keep-all`. Scale 14/16/20/28/40/56.
- Spacing: 4/8/16/24/32/48/64; radius 12px; icon stroke 2px.
- Voice: 3 adjectives (따뜻한, 간결한, 위트 있는), do "오늘도 한 잔 하실래요?" / don't "구매하세요!!!".

## Guide page skeleton (palette swatches that show contrast)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>모닝브루 브랜드 가이드</title>
<style>
:root { --brand:#7c4a2d; --accent:#e4572e; --cream:#fff4e0; --ink:#2b1d14; --line:#e8d9c5; }
body { margin: 0; background: var(--cream); color: var(--ink); line-height: 1.7; word-break: keep-all;
  font-family: "Pretendard Variable", Pretendard, system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }
main { width: min(100% - 2rem, 56rem); margin: 0 auto; padding: 3rem 0; }
h1 { font-size: clamp(2rem, 6vw, 3rem); margin: 0 0 .5rem; letter-spacing: -.01em; }
h2 { margin: 3rem 0 1rem; font-size: 1.5rem; border-bottom: 2px solid var(--line); padding-bottom: .5rem; }
.sw { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 12px; }
.sw div { border-radius: 14px; padding: 4.5rem .75rem .75rem; font-size: .8125rem; font-weight: 600; border: 1px solid var(--line); }
.row { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }
.tile { padding: 24px; border-radius: 16px; border: 1px solid var(--line); }
</style></head>
<body><main>
<h1>모닝브루 브랜드 가이드</h1><p>아침을 여는 한 잔, 따뜻하고 간결하게.</p>
<h2>색상</h2>
<div class="sw">
  <div style="background:#7c4a2d;color:#fff">Brand<br>#7c4a2d</div>
  <div style="background:#e4572e;color:#fff">Accent<br>#e4572e</div>
  <div style="background:#fff4e0;color:#2b1d14">Cream<br>#fff4e0</div>
  <div style="background:#2b1d14;color:#fff4e0">Ink<br>#2b1d14</div>
</div>
<h2>로고 변형</h2>
<div class="row">
  <div class="tile" style="background:#fff"><svg viewBox="0 0 64 64" width="64" height="64" aria-label="라이트 아이콘"><rect width="64" height="64" rx="16" fill="#7c4a2d"/><path d="M18 28h24v8a12 12 0 0 1-24 0z" fill="#fff4e0"/></svg></div>
  <div class="tile" style="background:#2b1d14"><svg viewBox="0 0 64 64" width="64" height="64" aria-label="다크 아이콘"><rect width="64" height="64" rx="16" fill="#fff4e0"/><path d="M18 28h24v8a12 12 0 0 1-24 0z" fill="#7c4a2d"/></svg></div>
  <div class="tile" style="background:#e4572e"><svg viewBox="0 0 64 64" width="64" height="64" aria-label="한 색 아이콘"><path d="M18 28h24v8a12 12 0 0 1-24 0z" fill="#fff"/></svg></div>
</div>
<h2>타이포그래피</h2>
<p style="font-size:2.5rem;font-weight:800;margin:0">오늘의 원두</p><p>본문은 Pretendard 16px, 행간 1.7. 짧고 따뜻한 문장을 씁니다.</p>
</main></body></html>
```

## Social avatar (400x400, circle-safe) and Open Graph card (1200x630)
```html
<svg viewBox="0 0 400 400" width="200" height="200" role="img" aria-label="프로필 이미지" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="400" fill="#7c4a2d"/>
  <g transform="translate(100 100) scale(3.125)"><path d="M18 28h24v8a12 12 0 0 1-24 0z" fill="#fff4e0"/><path d="M42 30h4a5 5 0 0 1 0 10h-4" fill="none" stroke="#fff4e0" stroke-width="3" stroke-linecap="round"/></g>
</svg>
<svg viewBox="0 0 1200 630" width="600" height="315" role="img" aria-label="소셜 카드" xmlns="http://www.w3.org/2000/svg">
  <rect width="1200" height="630" fill="#fff4e0"/>
  <rect x="80" y="80" width="140" height="140" rx="36" fill="#7c4a2d"/>
  <text x="80" y="360" font-family="Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif" font-size="84" font-weight="800" fill="#2b1d14">아침을 여는 한 잔</text>
  <text x="80" y="440" font-family="Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif" font-size="36" fill="#7c4a2d">모닝브루 · 매일 7시 오픈</text>
</svg>
```
The avatar mark stays within the central 70% so circular crops never cut it. OG tags: `<meta property="og:title" content="모닝브루">`, `<meta property="og:image" content="og.png">` (PNG/JPG, SVG is not accepted by most platforms).

## Export checklist
1. Save the icon SVG as `favicon.svg` (add `<style>@media (prefers-color-scheme: dark){...}</style>` inside the SVG if the mark must invert).
2. Make PNGs (browser: open the SVG, screenshot; or Inkscape/ImageMagick): 32, 180 (solid bg), 192, 512 (maskable).
3. Check at 16px, on white, on `#0b1020`, and in grayscale; the mark must stay recognizable.
