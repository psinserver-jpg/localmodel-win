---
name: menu-hud-game
description: Complete runnable neon mini-game with start menu, HUD (score, health bar, best score), game-over screen, screen shake, localStorage high score, keyboard and pointer control over a canvas.
triggers: [full game example, game menu example, hud example, start menu, game over screen, canvas overlay, neon game, dodge game, health bar, high score, localstorage, 게임 예제, 시작 메뉴, 게임 오버 화면, 체력바, 하이스코어, 오버레이, 네온 게임]
---
# Full example: menu + HUD + game over over a canvas

```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>별똥별 피하기</title>
<link href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
<style>
:root { --ink:#e0f2fe; --neon:#22d3ee; --pink:#e879f9; --bg:#07070f; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: "Orbitron", "Black Han Sans", sans-serif; word-break: keep-all; }
#game { position: relative; width: 100%; height: 100vh; height: 100dvh; overflow: hidden; user-select: none; touch-action: none; }
canvas { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
#hud { position: absolute; inset: 0; pointer-events: none; display: flex; justify-content: space-between; align-items: flex-start;
  padding: max(12px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 12px max(16px, env(safe-area-inset-left)); font-size: 22px; text-shadow: 0 0 8px var(--neon), 0 2px 0 #000; }
.bar { width: 160px; height: 14px; border: 2px solid var(--neon); border-radius: 8px; overflow: hidden; margin-top: 6px; }
.bar i { display: block; height: 100%; background: #22c55e; transform-origin: left; transition: transform .2s, background .2s; }
.screen { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 14px; text-align: center; background: rgb(7 7 15 / .82); }
.screen[hidden], #hud[hidden] { display: none; }
.screen h1 { margin: 0 0 8px; font-size: clamp(2rem, 8vw, 4rem); color: var(--neon); text-shadow: 0 0 12px var(--neon), 0 0 32px var(--neon); }
.screen p { margin: 0; opacity: .85; line-height: 1.7; }
.btn { min-width: 220px; min-height: 56px; padding: 0 24px; font: inherit; font-size: 20px; color: var(--ink); background: transparent;
  border: 2px solid var(--neon); border-radius: 12px; cursor: pointer; touch-action: manipulation; transition: transform .1s, box-shadow .2s; }
.btn:hover, .btn:focus-visible { box-shadow: 0 0 16px var(--neon); outline: none; }
.btn:active { transform: scale(.96); }
.shake { animation: shake .3s; }
@keyframes shake { 20% { transform: translate(-6px, 3px); } 40% { transform: translate(5px, -4px); } 60% { transform: translate(-4px, -2px); } 80% { transform: translate(3px, 3px); } }
@media (prefers-reduced-motion: reduce) { .shake { animation: none; } }
</style></head>
<body>
<div id="game">
  <canvas id="cv"></canvas>
  <div id="hud" hidden><div>점수 <b id="score">0</b><div class="bar" aria-label="체력"><i id="hp"></i></div></div><div>최고 <b id="best">0</b></div></div>
  <section class="screen" id="menu"><h1>별똥별 피하기</h1><p>방향키 또는 터치로 이동<br>최고 기록 <b id="menuBest">0</b></p><button class="btn" id="start" autofocus>시작하기</button></section>
  <section class="screen" id="over" hidden><h1>게임 오버</h1><p>점수 <b id="finalScore">0</b></p><button class="btn" id="again">다시 하기</button></section>
</div>
<script>
const $ = (id) => document.getElementById(id);
const game = $('game'), cv = $('cv'), ctx = cv.getContext('2d');
let W = 0, H = 0, state = 'menu', score = 0, hp = 1, last = 0, rocks = [], px = 0;
const KEY = 'lmw-hiscore-star-dodge';
function loadBest() { try { return Number(localStorage.getItem(KEY)) || 0; } catch (e) { return 0; } }
function saveBest(v) { try { localStorage.setItem(KEY, String(v)); } catch (e) { /* storage blocked */ } }
function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  W = cv.clientWidth; H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
new ResizeObserver(resize).observe(cv);
function setState(s) {
  state = s;
  $('menu').hidden = s !== 'menu'; $('over').hidden = s !== 'over'; $('hud').hidden = s !== 'playing';
  if (s === 'playing') { score = 0; hp = 1; rocks = []; px = W / 2; last = performance.now(); requestAnimationFrame(tick); }
  if (s === 'over') {
    $('finalScore').textContent = score;
    if (score > loadBest()) saveBest(score);
    $('menuBest').textContent = loadBest();
  }
}
function hit() {
  hp = Math.max(0, hp - 0.25);
  game.classList.remove('shake'); void game.offsetWidth; game.classList.add('shake');
  if (hp <= 0) setState('over');
}
function tick(t) {
  if (state !== 'playing') return;
  const dt = Math.min((t - last) / 1000, 0.05); last = t;
  if (Math.random() < dt * 2.2) rocks.push({ x: Math.random() * W, y: -20, v: 160 + Math.random() * 160 });
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#e879f9';
  rocks = rocks.filter((r) => {
    r.y += r.v * dt;
    ctx.beginPath(); ctx.arc(r.x, r.y, 10, 0, Math.PI * 2); ctx.fill();
    if (Math.abs(r.x - px) < 24 && Math.abs(r.y - (H - 60)) < 24) { hit(); return false; }
    if (r.y > H + 20) { score += 10; return false; }
    return true;
  });
  ctx.fillStyle = '#22d3ee'; ctx.fillRect(px - 18, H - 72, 36, 24);
  $('score').textContent = score; $('best').textContent = Math.max(score, loadBest());
  $('hp').style.transform = 'scaleX(' + hp + ')';
  $('hp').style.background = hp > 0.5 ? '#22c55e' : hp > 0.25 ? '#f59e0b' : '#ef4444';
  requestAnimationFrame(tick);
}
const keys = {};
function togglePause() {
  if (state === 'playing') state = 'paused';
  else if (state === 'paused') { state = 'playing'; last = performance.now(); requestAnimationFrame(tick); }
}
addEventListener('keydown', (e) => { keys[e.key] = true; if (e.key === 'p' || e.key === 'Escape') togglePause(); });
document.addEventListener('visibilitychange', () => { if (document.hidden && state === 'playing') state = 'paused'; });
addEventListener('keyup', (e) => { keys[e.key] = false; });
setInterval(() => { if (state === 'playing') px = Math.min(W - 20, Math.max(20, px + ((keys.ArrowRight || keys.d ? 1 : 0) - (keys.ArrowLeft || keys.a ? 1 : 0)) * 14)); }, 16);
game.addEventListener('pointermove', (e) => { if (state === 'playing') px = e.clientX; });
$('start').addEventListener('click', () => setState('playing'));
$('again').addEventListener('click', () => setState('playing'));
$('menuBest').textContent = loadBest();
</script>
</body></html>
```

