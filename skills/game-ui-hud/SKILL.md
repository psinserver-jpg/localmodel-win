---
name: game-ui-hud
description: UI for browser games - start, pause, game-over and settings menus, HUD (score, health, timer), pixel/neon/cartoon/sci-fi style kits, touch controls, screen shake, high score, overlays on a canvas. Use for game menus, HUDs, game styling and mobile game controls.
triggers: [game ui, game menu, hud, health bar, score, scoreboard, game over, pause menu, start screen, main menu, high score, joystick, virtual joystick, touch controls, d-pad, pixel art, retro, 8-bit, arcade, overlay, screen shake, canvas game, game design, 게임, 게임 ui, 게임 화면, 시작 화면, 메뉴, 일시정지, 게임 오버, 점수, 체력바, 하이스코어, 조이스틱, 터치 컨트롤, 픽셀, 레트로, 아케이드, 오버레이, 화면 흔들림]
priority: 48
---
# Game UI and HUD

DOM overlay on top of a `<canvas>`: canvas draws the world, HTML/CSS draws menus + HUD (crisp text, accessible, easy to style). Single file, no libraries.

## Structure rules
1. `#game` wrapper: `position: relative; width: 100%; height: 100dvh; overflow: hidden; user-select: none; touch-action: none;`. Canvas `position:absolute; inset:0`. `#hud` and `.screen` overlays `position:absolute; inset:0`. HUD `pointer-events: none` (except its buttons).
2. State machine in JS: `state = 'menu' | 'playing' | 'paused' | 'over'`; ONE function `setState(s)` toggles `hidden` on screens and starts/stops the loop. Escape / P toggles pause; auto-pause on `visibilitychange` and `blur`.
3. Menus: big centered column, title 48-72px, 3-4 buttons max (Start, Settings, How to play), each >= 56px tall, focusable, arrow keys + Enter work, first button autofocus. Show key hints ("이동: 방향키 / WASD  점프: 스페이스  일시정지: P").
4. HUD: corners only (score top-left, health top-right or bottom-left, timer top-center), padded with `env(safe-area-inset-*)`, text 20-28px, thick outline for readability over any background (`paint-order: stroke fill; -webkit-stroke: 3px #000` or multi text-shadow). Never cover the center play area.
5. Health bar: outer track + inner fill with `transform: scaleX(hp)` (`transform-origin: left`), color by threshold (>50% green `#22c55e`, >25% amber `#f59e0b`, else red `#ef4444` + pulse). Also show the number for accessibility.
6. Feedback: hit = screen shake (CSS keyframes, 300ms) + red flash overlay; score gain = floating "+100" pop that rises and fades (400-700ms); level-up = scale pulse. Respect `prefers-reduced-motion` (no shake).
7. High score: `localStorage` inside try/catch (`lmw-hiscore-<gamename>`), shown on menu and game-over with "NEW BEST!" badge.
8. Touch: show virtual controls only on touch devices (`@media (pointer: coarse)`); left = joystick or d-pad, right = 1-2 action buttons 72-88px, semi-transparent (`rgb(255 255 255 / .2)`), placed above the bottom safe area; use pointer events with `setPointerCapture` and multi-touch (track by `pointerId`).
9. Canvas: fit to wrapper with DPR scaling; `image-rendering: pixelated` for pixel art; fixed logical resolution (e.g. 320x180) scaled up gives a retro look for free.
10. Korean text: `word-break: keep-all`; use a Korean-capable font for ALL game text (Press Start 2P / Orbitron have NO Hangul and fall back to the system font).

## Style kits (pick one, keep consistent)
- Pixel/retro: Google Font `Press Start 2P` (Latin) 10-16px sizes, Korean `DungGeunMo` (CDN: `https://cdn.jsdelivr.net/gh/projectnoonnu/noonfonts_six@1.2/DungGeunMo.woff` as @font-face) or `Silkscreen`; palette `#0f0f1b #1a1c2c #5d275d #b13e53 #ef7d57 #ffcd75 #a7f070 #38b764 #41a6f6 #f4f4f4`; hard 4px offset shadows, `border: 4px solid`, no radius, `image-rendering: pixelated`.
- Neon/arcade: `Orbitron` 700-900 (Korean: `Black Han Sans`), bg `#07070f`, cyan `#22d3ee`, magenta `#e879f9`, lime `#a3e635`; glow `text-shadow: 0 0 8px currentColor, 0 0 24px currentColor`; thin 2px borders with glow `box-shadow`.
- Cartoon: `Bungee` or `Jua` (Korean), bright `#ffd23f #ff6b6b #4ecdc4 #1a535c`, thick 4px dark outline `#1a1a2e`, radius 16-24px, bottom-heavy shadow `0 6px 0 #1a1a2e`, buttons squish on `:active` (translateY(4px), shadow 2px).
- Sci-fi: `Orbitron` + `Rajdhani`, bg `#050b14`, accent `#38bdf8`, `#f97316` warnings; chamfered corners with `clip-path: polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px)`.

## State machine + HUD core (copy; full game in reference/menu-hud-game.md)
```html
<div id="game"><canvas id="cv"></canvas>
  <div id="hud"><span>점수 <b id="score">0</b></span><div class="bar"><i id="hp"></i></div></div>
  <section class="screen" id="menu"><h1>별똥별 피하기</h1><button class="btn" id="start">시작하기</button></section>
  <section class="screen" id="over" hidden><h1>게임 오버</h1><button class="btn" id="again">다시 하기</button></section></div>
<style>
#game { position: relative; height: 100dvh; overflow: hidden; touch-action: none; }
#game canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
#hud { position: absolute; inset: 0 0 auto 0; display: flex; justify-content: space-between; pointer-events: none; padding: max(12px, env(safe-area-inset-top)) 16px; font-size: 22px; text-shadow: 0 2px 0 #000; }
.bar { width: 160px; height: 14px; border: 2px solid #22d3ee; border-radius: 8px; overflow: hidden; }
.bar i { display: block; height: 100%; background: #22c55e; transform-origin: left; }
.screen { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 14px; background: rgb(7 7 15 / .82); }
.screen[hidden], #hud[hidden] { display: none; }
.btn { min-width: 220px; min-height: 56px; font: inherit; font-size: 20px; border-radius: 12px; cursor: pointer; }
.shake { animation: shake .3s; }
@keyframes shake { 20% { transform: translate(-6px, 3px); } 60% { transform: translate(-4px, -2px); } 80% { transform: translate(3px, 3px); } }
</style>
<script>
const $ = (id) => document.getElementById(id);
let state = 'menu';
function setState(s) {
  state = s;
  $('menu').hidden = s !== 'menu'; $('over').hidden = s !== 'over'; $('hud').hidden = s === 'menu' || s === 'over';
}
function hurt(hp) {
  $('hp').style.transform = 'scaleX(' + hp + ')';
  $('hp').style.background = hp > 0.5 ? '#22c55e' : hp > 0.25 ? '#f59e0b' : '#ef4444';
  $('game').classList.remove('shake'); void $('game').offsetWidth; $('game').classList.add('shake');
}
$('start').onclick = $('again').onclick = () => setState('playing');
addEventListener('keydown', (e) => { if (e.key === 'p' && state !== 'over') setState(state === 'playing' ? 'paused' : 'playing'); });
</script>
```

## Pitfalls
- Pause leaves rAF running: check `state` at the top of `tick` and restart with fresh `last`, or dt explodes.
- Canvas pointer coordinates differ from CSS pixels if canvas is scaled: convert via `getBoundingClientRect`.
- More: reference/hud-kit.md (menus, settings, floating score, health, timer, countdown), reference/touch-controls.md (virtual joystick, buttons, key hints).
