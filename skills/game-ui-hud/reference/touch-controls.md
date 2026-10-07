---
name: touch-controls
description: Virtual joystick and action buttons with pointer events (multi-touch), keyboard hint chips, floating score pop, countdown, timer, settings menu with sound and volume toggles stored in localStorage.
triggers: [virtual joystick, joystick, d-pad, touch controls, action button, multi-touch, pointer events, keyboard hint, key hint, floating score, score pop, countdown, timer, settings menu, volume, sound toggle, 가상 조이스틱, 조이스틱, 터치 컨트롤, 액션 버튼, 키 안내, 점수 팝업, 카운트다운, 타이머, 설정 메뉴, 볼륨, 소리 설정]
---
# Touch controls, hints, pops, settings

## Virtual joystick + action button (multi-touch, pointer events)
```html
<style>
.touch { display: none; }
@media (pointer: coarse) { .touch { display: block; } }
.stick { position: absolute; left: max(24px, env(safe-area-inset-left)); bottom: max(24px, env(safe-area-inset-bottom)); width: 140px; height: 140px;
  border-radius: 50%; background: rgb(255 255 255 / .12); border: 2px solid rgb(255 255 255 / .3); touch-action: none; }
.knob { position: absolute; left: 50%; top: 50%; width: 60px; height: 60px; margin: -30px 0 0 -30px; border-radius: 50%; background: rgb(255 255 255 / .5); }
.abtn { position: absolute; right: max(24px, env(safe-area-inset-right)); bottom: max(40px, env(safe-area-inset-bottom)); width: 84px; height: 84px;
  border-radius: 50%; border: 2px solid rgb(255 255 255 / .4); background: rgb(34 211 238 / .3); color: #fff; font: 700 18px system-ui; touch-action: none; user-select: none; }
.abtn.down { background: rgb(34 211 238 / .6); transform: scale(.94); }
</style>
<div class="touch"><div class="stick" id="stick"><div class="knob" id="knob"></div></div><button class="abtn" id="abtn" aria-label="점프">점프</button></div>
<script>
const input = { x: 0, y: 0, action: false };
const stick = document.getElementById('stick');
const knob = document.getElementById('knob');
const RADIUS = 50;
let stickId = null;
function moveKnob(e) {
  const r = stick.getBoundingClientRect();
  let dx = e.clientX - (r.left + r.width / 2);
  let dy = e.clientY - (r.top + r.height / 2);
  const len = Math.hypot(dx, dy);
  if (len > RADIUS) { dx = (dx / len) * RADIUS; dy = (dy / len) * RADIUS; }
  knob.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
  input.x = dx / RADIUS; input.y = dy / RADIUS;
}
function releaseKnob() { stickId = null; knob.style.transform = ''; input.x = 0; input.y = 0; }
stick.addEventListener('pointerdown', (e) => { if (stickId !== null) return; stickId = e.pointerId; stick.setPointerCapture(e.pointerId); moveKnob(e); });
stick.addEventListener('pointermove', (e) => { if (e.pointerId === stickId) moveKnob(e); });
stick.addEventListener('pointerup', (e) => { if (e.pointerId === stickId) releaseKnob(); });
stick.addEventListener('pointercancel', releaseKnob);
const abtn = document.getElementById('abtn');
abtn.addEventListener('pointerdown', (e) => { abtn.setPointerCapture(e.pointerId); input.action = true; abtn.classList.add('down'); });
const upA = () => { input.action = false; abtn.classList.remove('down'); };
abtn.addEventListener('pointerup', upA);
abtn.addEventListener('pointercancel', upA);
addEventListener('contextmenu', (e) => e.preventDefault());
</script>
```
Read `input.x/input.y/input.action` in your game loop (merge with keyboard: `x = input.x || (keys.d ? 1 : 0) - (keys.a ? 1 : 0)`). Keyboard users: no on-screen controls needed.

## Keyboard hint chips
```css
.hints { display: flex; flex-wrap: wrap; gap: 8px 16px; justify-content: center; font-size: 14px; opacity: .85; }
kbd { display: inline-block; min-width: 28px; padding: 2px 8px; border: 2px solid currentColor; border-bottom-width: 4px; border-radius: 6px; font: 700 13px/1.4 ui-monospace, Menlo, Consolas, monospace; text-align: center; }
@media (pointer: coarse) { .hints { display: none; } }
```
HTML: `<span><kbd>W</kbd><kbd>A</kbd><kbd>S</kbd><kbd>D</kbd> 이동</span> <span><kbd>Space</kbd> 점프</span> <span><kbd>P</kbd> 일시정지</span>`.

## Floating score pop + level-up pulse
```css
.pop { position: absolute; pointer-events: none; font-weight: 900; font-size: 28px; color: #fde047; text-shadow: 0 2px 0 #000, 0 0 12px #f59e0b; animation: pop .7s ease-out forwards; }
@keyframes pop { from { opacity: 1; transform: translateY(0) scale(.6); } 30% { transform: translateY(-14px) scale(1.2); } to { opacity: 0; transform: translateY(-60px) scale(1); } }
.pulse { animation: pulse .4s ease-out; }
@keyframes pulse { 50% { transform: scale(1.3); } }
.flash { position: absolute; inset: 0; background: #ef4444; opacity: 0; pointer-events: none; animation: flash .25s ease-out; }
@keyframes flash { from { opacity: .35; } to { opacity: 0; } }
```
```js
// fragment: host is the #game element, x/y in CSS px inside it
function scorePop(host, x, y, text) {
  const el = document.createElement('div');
  el.className = 'pop';
  el.textContent = text;
  el.style.left = x + 'px';
  el.style.top = y + 'px';
  host.appendChild(el);
  el.addEventListener('animationend', () => el.remove());
}
function flashScreen(host) {
  const f = document.createElement('div');
  f.className = 'flash';
  host.appendChild(f);
  f.addEventListener('animationend', () => f.remove());
}
```

## Countdown 3-2-1-시작! and mm:ss timer
```js
// fragment: el is a big centered element; resolves when finished
function countdown(el, from = 3) {
  return new Promise((resolve) => {
    let n = from;
    const step = () => {
      el.textContent = n > 0 ? String(n) : '시작!';
      el.classList.remove('pulse'); void el.offsetWidth; el.classList.add('pulse');
      if (n-- < 0) { el.textContent = ''; resolve(); return; }
      setTimeout(step, 800);
    };
    step();
  });
}
const mmss = (sec) => String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(Math.floor(sec % 60)).padStart(2, '0');
```
Drive timers from game `dt` (sum of dt), not `setInterval`, so pause stops the clock.

## Settings menu with persisted options
```html
<section class="screen" id="settings" hidden>
  <h1>설정</h1>
  <label><input type="checkbox" id="optSound" checked> 효과음</label>
  <label>음량 <input type="range" id="optVol" min="0" max="100" value="70"></label>
  <label><input type="checkbox" id="optShake" checked> 화면 흔들림</label>
  <button class="btn" id="settingsBack">돌아가기</button>
</section>
<script>
const SKEY = 'lmw-settings-mygame';
const defaults = { sound: true, vol: 70, shake: !matchMedia('(prefers-reduced-motion: reduce)').matches };
let settings = { ...defaults };
try { settings = { ...defaults, ...JSON.parse(localStorage.getItem(SKEY) || '{}') }; } catch (e) { /* ignore */ }
const optSound = document.getElementById('optSound');
const optVol = document.getElementById('optVol');
const optShake = document.getElementById('optShake');
optSound.checked = settings.sound; optVol.value = settings.vol; optShake.checked = settings.shake;
function saveSettings() {
  settings = { sound: optSound.checked, vol: Number(optVol.value), shake: optShake.checked };
  try { localStorage.setItem(SKEY, JSON.stringify(settings)); } catch (e) { /* ignore */ }
}
[optSound, optVol, optShake].forEach((o) => o.addEventListener('input', saveSettings));
</script>
```
Sound: create `new AudioContext()` only after the first user click (autoplay policy); simple beep = oscillator `type='square'`, frequency 440-880, gain ramp to 0.0001 over 120ms, multiplied by `settings.vol / 100`.
