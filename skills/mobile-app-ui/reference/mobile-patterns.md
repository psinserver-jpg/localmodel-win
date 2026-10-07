---
name: mobile-patterns
description: Working mobile web patterns - bottom sheet with drag-to-close, swipe actions on list rows, pull-to-refresh, virtual keyboard handling with visualViewport, PWA manifest and meta tags, install hints.
triggers: [bottom sheet, drawer, swipe action, swipe to delete, pull to refresh, pull-to-refresh, gesture, pointer events, virtual keyboard, visualviewport, keyboard, pwa, manifest, add to home screen, apple-touch-icon, standalone, 바텀시트, 스와이프 삭제, 당겨서 새로고침, 제스처, 가상 키보드, 키보드, 홈 화면 추가, 매니페스트]
---
# Mobile patterns

## Bottom sheet with drag-to-close
```html
<style>
.scrim { position: fixed; inset: 0; background: rgb(0 0 0 / .45); opacity: 0; pointer-events: none; transition: opacity .25s; }
.sheet { position: fixed; left: 0; right: 0; bottom: 0; max-height: 85dvh; display: flex; flex-direction: column;
  background: var(--surface, #fff); border-radius: 20px 20px 0 0; padding: 8px 16px calc(16px + env(safe-area-inset-bottom));
  transform: translateY(100%); transition: transform .3s cubic-bezier(.2,.8,.2,1); touch-action: none; }
.open .scrim { opacity: 1; pointer-events: auto; }
.open .sheet { transform: translateY(0); }
.sheet.drag { transition: none; }
.grab { width: 40px; height: 5px; border-radius: 3px; background: #9ca3af; margin: 4px auto 12px; }
.sheet .body { overflow-y: auto; overscroll-behavior: contain; touch-action: pan-y; }
</style>
<div id="root"><button id="openBtn">필터 열기</button>
  <div class="scrim" id="scrim"></div>
  <div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-label="필터">
    <div class="grab" id="grab"></div><div class="body"><h2>필터</h2><p>가격, 브랜드, 배송 방법을 선택하세요.</p></div></div></div>
<script>
const root = document.getElementById('root');
const sheet = document.getElementById('sheet');
const grab = document.getElementById('grab');
const open = () => root.classList.add('open');
const close = () => { root.classList.remove('open'); sheet.style.transform = ''; };
document.getElementById('openBtn').addEventListener('click', open);
document.getElementById('scrim').addEventListener('click', close);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
let startY = 0, dy = 0, dragging = false;
grab.style.touchAction = 'none';
grab.addEventListener('pointerdown', (e) => { dragging = true; startY = e.clientY; dy = 0; sheet.classList.add('drag'); grab.setPointerCapture(e.pointerId); });
grab.addEventListener('pointermove', (e) => { if (!dragging) return; dy = Math.max(0, e.clientY - startY); sheet.style.transform = 'translateY(' + dy + 'px)'; });
function endDrag() { if (!dragging) return; dragging = false; sheet.classList.remove('drag'); if (dy > 100) close(); else sheet.style.transform = ''; }
grab.addEventListener('pointerup', endDrag);
grab.addEventListener('pointercancel', endDrag);
</script>
```
Drag only from the grab handle, so inner scrolling keeps working.

## Swipe-to-reveal row action (left swipe)
```html
<style>
.row { position: relative; overflow: hidden; border-radius: 14px; margin-bottom: 8px; background: #dc2626; }
.row .del { position: absolute; right: 0; top: 0; bottom: 0; width: 88px; border: 0; background: transparent; color: #fff; font-weight: 700; }
.row .fg { position: relative; background: var(--surface, #fff); padding: 16px; min-height: 56px; touch-action: pan-y; transition: transform .2s; }
</style>
<div class="row"><button class="del">삭제</button><div class="fg">우유 1L 사기</div></div>
<script>
document.querySelectorAll('.row').forEach((row) => {
  const fg = row.querySelector('.fg');
  let x0 = 0, dx = 0, on = false;
  fg.addEventListener('pointerdown', (e) => { on = true; x0 = e.clientX; fg.style.transition = 'none'; fg.setPointerCapture(e.pointerId); });
  fg.addEventListener('pointermove', (e) => { if (!on) return; dx = Math.min(0, Math.max(-88, e.clientX - x0)); fg.style.transform = 'translateX(' + dx + 'px)'; });
  const end = () => { if (!on) return; on = false; fg.style.transition = ''; fg.style.transform = dx < -44 ? 'translateX(-88px)' : ''; };
  fg.addEventListener('pointerup', end);
  fg.addEventListener('pointercancel', end);
  row.querySelector('.del').addEventListener('click', () => row.remove());
});
</script>
```
Always provide a non-gesture way too (a visible menu button), since swipes are undiscoverable.

## Pull-to-refresh (scroll container at top)
```html
<style>
#list { height: 100dvh; overflow-y: auto; overscroll-behavior-y: contain; touch-action: pan-y; }
#ptr { height: 0; overflow: hidden; display: grid; place-items: center; color: #6b7280; font-size: 14px; }
</style>
<div id="list"><div id="ptr">당겨서 새로고침</div><div id="content">마지막 갱신: 방금</div></div>
<script>
const list = document.getElementById('list');
const ptr = document.getElementById('ptr');
let y0 = 0, pull = 0, active = false;
list.addEventListener('touchstart', (e) => { if (list.scrollTop === 0) { y0 = e.touches[0].clientY; active = true; } }, { passive: true });
list.addEventListener('touchmove', (e) => {
  if (!active) return;
  pull = Math.max(0, (e.touches[0].clientY - y0) * 0.5);
  if (pull > 0) { ptr.style.height = Math.min(pull, 72) + 'px'; ptr.textContent = pull > 60 ? '놓으면 새로고침' : '당겨서 새로고침'; }
}, { passive: true });
list.addEventListener('touchend', () => {
  if (!active) return;
  active = false;
  if (pull > 60) {
    ptr.textContent = '새로고침 중...';
    setTimeout(() => { document.getElementById('content').textContent = '마지막 갱신: ' + new Date().toLocaleTimeString('ko-KR'); ptr.style.height = '0'; }, 800);
  } else { ptr.style.height = '0'; }
  pull = 0;
});
</script>
```

## Virtual keyboard
```js
// keep a bottom composer above the keyboard (iOS Safari does not resize the layout viewport)
const bar = document.querySelector('.composer');
const vv = window.visualViewport;
function fit() {
  if (!vv || !bar) return;
  const covered = window.innerHeight - vv.height - vv.offsetTop;
  bar.style.transform = 'translateY(' + (-Math.max(0, covered)) + 'px)';
}
if (vv) { vv.addEventListener('resize', fit); vv.addEventListener('scroll', fit); }
```
Alternatives: keep the composer as a normal flex child at the bottom of a `100dvh` flex column (Android Chrome resizes `dvh` with the keyboard when `interactive-widget=resizes-content` is added to the viewport meta). Scroll the focused input into view: `input.scrollIntoView({ block: 'center', behavior: 'smooth' })`.

## PWA basics (no service worker)
```html
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="하루할일">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon.svg" type="image/svg+xml">
```
manifest.webmanifest (separate file; a single-file page can embed it with a Blob URL):
```json
{ "name": "하루할일", "short_name": "하루할일", "start_url": "./index.html", "display": "standalone",
  "orientation": "portrait", "background_color": "#ffffff", "theme_color": "#2563eb", "lang": "ko",
  "icons": [ { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
             { "src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" } ] }
```
Installability on Android Chrome needs HTTPS (or localhost), a manifest with name, icons 192 and 512, and start_url; iOS: Share, then "홈 화면에 추가". File double-click (file://) cannot be installed; the page still works as a normal web app. Icons: keep the logo inside the central 80% (maskable safe zone).

## Standalone detection and install hint
```js
const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
if (!standalone && /iphone|ipad/i.test(navigator.userAgent)) {
  document.getElementById('hint')?.removeAttribute('hidden');
}
```
