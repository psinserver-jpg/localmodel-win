---
name: mobile-app-ui
description: Mobile-first app UI built as web - touch targets, bottom tab bar, bottom sheets, safe-area insets, dvh, virtual keyboard, gestures, mobile forms, iOS vs Android look, PWA manifest. Use for mobile apps, phone-sized screens, PWAs and touch interfaces.
triggers: [mobile app, mobile ui, mobile first, mobile-first, phone, smartphone, ios, android, pwa, touch, tab bar, bottom navigation, bottom sheet, safe area, swipe, pull to refresh, app screen, webview, responsive app, manifest, 모바일, 모바일 앱, 앱 화면, 앱 ui, 스마트폰, 터치, 하단 탭, 바텀시트, 바텀 시트, 스와이프, 안드로이드, 아이폰, 앱 만들기, 홈 화면에 추가]
priority: 48
---
# Mobile app UI (web)

Design at 390x844 first (iPhone 14) and check 360x640. Result must work as one HTML file opened on a phone.

## Hard rules
1. Head: `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` (cover is REQUIRED for safe-area insets). Never `user-scalable=no` or `maximum-scale=1` (accessibility).
2. Touch targets >= 44x44px (iOS) / 48dp (Android); spacing between targets >= 8px. Icon buttons: 44px box around a 24px icon.
3. Thumb zone: primary actions in the bottom third. Navigation = bottom tab bar (3-5 items, icon + label 11-12px), not a hamburger. Top bar only for title + 1-2 actions.
4. Full height = `min-height: 100dvh` (fallback line `100vh` BEFORE it). Never `100vh` alone (URL bar covers content).
5. Safe areas: `padding-bottom: env(safe-area-inset-bottom)` on tab bars/sheets/sticky buttons; `padding-top: env(safe-area-inset-top)` on headers; use `max(16px, env(safe-area-inset-left))` for side gutters.
6. Text: body 16px minimum (inputs MUST be >= 16px or iOS Safari zooms on focus). Line-height 1.5. Korean: `word-break: keep-all`, Pretendard / `system-ui, "Apple SD Gothic Neo", "Noto Sans KR"`.
7. Remove tap delay/highlight: `touch-action: manipulation; -webkit-tap-highlight-color: transparent;` on interactive elements. Add `:active` feedback (`transform: scale(.97)` or bg tint), since hover does not exist. Gate hover styles with `@media (hover: hover)`.
8. `overscroll-behavior: contain` on sheets and inner scrollers; `-webkit-overflow-scrolling` is not needed anymore.
9. Prevent text selection only on controls (`user-select: none`), never on content.
10. Dark mode via tokens + `color-scheme: light dark`; `<meta name="theme-color">` for both schemes.
11. Performance: animate `transform`/`opacity` only; images `loading="lazy"` with width/height; avoid big blurs and `box-shadow` animation; long lists > 100 rows paginate or use `content-visibility: auto; contain-intrinsic-size: auto 72px`.
12. Platform feel: iOS = large titles, 17px, SF-like system font, rounded 12-14px cards, sheets from the bottom, segmented controls; Android (Material 3) = 16px body, 12-28px radii, FAB, filled tonal buttons, top app bar. Pick `system-ui` so each gets its own font; do not mix both idioms in one app.

## Skeleton (app shell with top bar, scroll area, tab bar)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1115" media="(prefers-color-scheme: dark)">
<title>하루할일</title>
<style>
:root { color-scheme: light dark; --bg:#f5f6f8; --surface:#fff; --text:#111827; --muted:#6b7280; --line:#e5e7eb; --primary:#2563eb; }
@media (prefers-color-scheme: dark) { :root { --bg:#0f1115; --surface:#1a1d24; --text:#f3f4f6; --muted:#9ca3af; --line:#2a2f3a; --primary:#60a5fa; } }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { display: flex; flex-direction: column; min-height: 100vh; min-height: 100dvh; background: var(--bg); color: var(--text);
  font: 16px/1.5 system-ui, -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; word-break: keep-all; overscroll-behavior-y: none; }
header { padding: max(12px, env(safe-area-inset-top)) 16px 12px; background: var(--surface); border-bottom: 1px solid var(--line); font-size: 20px; font-weight: 700; }
main { flex: 1; overflow-y: auto; padding: 16px; display: grid; gap: 12px; align-content: start; overscroll-behavior: contain; }
.item { display: flex; align-items: center; gap: 12px; min-height: 56px; padding: 8px 16px; background: var(--surface); border-radius: 14px; touch-action: manipulation; }
.item:active { transform: scale(.98); }
nav { display: flex; background: var(--surface); border-top: 1px solid var(--line); padding-bottom: env(safe-area-inset-bottom); }
nav button { flex: 1; min-height: 56px; display: grid; place-items: center; gap: 2px; border: 0; background: none; color: var(--muted); font-family: inherit; font-size: 11px; font-weight: 600; line-height: 1; touch-action: manipulation; }
nav button[aria-current="page"] { color: var(--primary); }
nav svg { width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
</style></head>
<body>
<header>오늘 할 일</header>
<main><label class="item"><input type="checkbox" style="width:24px;height:24px"> 장보기 (우유, 달걀)</label>
<label class="item"><input type="checkbox" style="width:24px;height:24px"> 오후 3시 팀 회의</label></main>
<nav aria-label="하단 메뉴">
  <button aria-current="page"><svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8M5 10v10h14V10"/></svg>홈</button>
  <button><svg viewBox="0 0 24 24"><path d="M4 20V10M10 20V4M16 20v-7"/></svg>통계</button>
  <button><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg>내 정보</button>
</nav>
</body></html>
```

## Forms on phones
`<input type="email" inputmode="email" autocomplete="email" autocapitalize="off">`, phone `type="tel" inputmode="tel" autocomplete="tel"`, numbers `inputmode="numeric" pattern="[0-9]*"`, OTP `autocomplete="one-time-code"`, search `type="search" enterkeyhint="search"`. Label above input, height 48px, one column, submit button full width and sticky at bottom.

## Pitfalls
- Sticky bottom bar vs keyboard: use `position: sticky; bottom: 0` inside the scroll container (not `fixed`), or listen to `visualViewport` resize; see reference.
- `position: fixed` + `100vh` modal jumps on iOS; use `inset: 0` + `100dvh`.
- Pull-to-refresh and swipe: set `touch-action: pan-y` and handle `pointer*` events; see reference/mobile-patterns.md (bottom sheet, swipe actions, pull-to-refresh, PWA manifest, keyboard handling).
