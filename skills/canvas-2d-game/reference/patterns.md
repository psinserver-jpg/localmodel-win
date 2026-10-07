---
name: patterns
description: Complete breakout game (paddle by keys/mouse/touch, sub-stepped ball so it never tunnels, angle from hit position, levels, lives, particles, shake) plus short recipes for pong, snake, shooter, sprite sheets and sound. Verified with a bot, level-up, lose-life and game-over checks.
triggers: [breakout, 벽돌깨기, pong, 퐁, 핑퐁, snake, 스네이크, 뱀, shooter, 슈팅, 우주선, space invaders, 인베이더, paddle, 패들, ball, 공, brick, 벽돌, sprite, 스프라이트, 사운드, sound, 효과음, 아케이드, arcade, canvas game, 캔버스 게임]
---
# Breakout + recipes (breakout verified: bot kept the ball alive and broke bricks, clearing all bricks went to level 2, three misses gave game over, restart worked)

Pong = breakout with two paddles and no bricks: AI paddle `y += clamp(ball.y - ai.y, -speed*dt, speed*dt)`, score when the ball passes an edge, reflect with the hit-position angle as below. Snake: grid array, move every 0.12 s with an accumulator (not every frame), queue the next direction so two quick key presses in one tick do not reverse into yourself, `food` placed on a free cell, collision with own body or wall = game over. Shooter: player `x` follows the pointer, `bullets` array with `vy = -600`, enemies array, bullet-vs-enemy AABB, cooldown `shootTimer -= dt`. Sprite sheet from code: strings of digits mapped to a palette `{1:"#222",2:"#e53935"}`, draw once to an offscreen `canvas` and `drawImage` it every frame (fast). Beeps: `OscillatorNode` square wave 0.05 s at 300-900 Hz, created lazily after the first key/tap.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>벽돌깨기</title>
<style>
  html, body { margin: 0; height: 100%; background: #12121f; overflow: hidden; touch-action: none; user-select: none; }
  body { display: grid; place-items: center; font-family: system-ui, 'Pretendard', sans-serif; }
  canvas { width: min(100vw, 640px, calc(100vh * 0.75)); aspect-ratio: 480 / 640; background: #1c1c33; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const W = 480, H = 640, COLS = 8, ROWS = 6, BW = W / COLS, BH = 26, TOP = 70;
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
function fit() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2), r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
}
window.addEventListener('resize', fit); fit();

let mode = 'ready', score = 0, lives = 3, best = 0, level = 1, overAt = 0, acc = 0, last = 0, shake = 0;
try { best = Number(localStorage.getItem('breakout-best') || 0); } catch (e) { /* ignore */ }
const paddle = { x: W / 2, y: H - 50, w: 90, h: 14, vx: 0 };
const ball = { x: 0, y: 0, r: 8, vx: 0, vy: 0, stuck: true };
let bricks = [], sparks = [];
const keys = new Set();

function buildBricks() {
  bricks = [];
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) bricks.push({ x: c * BW, y: TOP + r * BH, w: BW, h: BH, hue: r * 50, alive: true });
}
function resetBall() { ball.stuck = true; ball.vx = ball.vy = 0; }
function startGame() { score = 0; lives = 3; level = 1; buildBricks(); resetBall(); sparks.length = 0; mode = 'playing'; }
function launch() {
  if (!ball.stuck) return;
  const speed = 360 + level * 40, a = -Math.PI / 2 + (Math.random() - 0.5) * 0.6;   // never launch flat
  ball.vx = Math.cos(a) * speed; ball.vy = Math.sin(a) * speed; ball.stuck = false;
}
function press() {
  if (mode === 'ready' || (mode === 'over' && performance.now() - overAt > 500)) startGame();
  else if (mode === 'playing') launch();
}
let audio = null;
function beep(f, d) {
  try { audio = audio || new AudioContext(); const o = audio.createOscillator(), g = audio.createGain(); o.type = 'square'; o.frequency.value = f; g.gain.value = 0.04; o.connect(g); g.connect(audio.destination); o.start(); o.stop(audio.currentTime + d); } catch (e) { /* audio blocked */ }
}
window.addEventListener('keydown', (e) => { if (['Space', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault(); if (e.code === 'Space' && !e.repeat) press(); keys.add(e.code); });
window.addEventListener('keyup', (e) => keys.delete(e.code));
window.addEventListener('blur', () => keys.clear());
let pointerX = null;                                   // mouse/touch: paddle follows the finger
canvas.addEventListener('pointermove', (e) => { pointerX = (e.clientX - canvas.getBoundingClientRect().left) / canvas.clientWidth * W; });
canvas.addEventListener('pointerdown', (e) => { pointerX = (e.clientX - canvas.getBoundingClientRect().left) / canvas.clientWidth * W; press(); });

function update(dt) {
  if (mode !== 'playing') return;
  const dir = (keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0);
  if (dir) { paddle.x += dir * 520 * dt; pointerX = null; } else if (pointerX !== null) paddle.x += (pointerX - paddle.x) * (1 - Math.exp(-25 * dt));
  paddle.x = Math.max(paddle.w / 2, Math.min(W - paddle.w / 2, paddle.x));
  if (ball.stuck) { ball.x = paddle.x; ball.y = paddle.y - ball.r - 1; return; }
  const steps = Math.ceil(Math.hypot(ball.vx, ball.vy) * dt / 6);   // sub-steps so a fast ball never tunnels through a brick
  for (let s = 0; s < steps; s++) {
    ball.x += ball.vx * dt / steps; ball.y += ball.vy * dt / steps;
    if (ball.x < ball.r) { ball.x = ball.r; ball.vx = Math.abs(ball.vx); }
    if (ball.x > W - ball.r) { ball.x = W - ball.r; ball.vx = -Math.abs(ball.vx); }
    if (ball.y < ball.r) { ball.y = ball.r; ball.vy = Math.abs(ball.vy); }
    if (ball.vy > 0 && ball.y + ball.r > paddle.y && ball.y - ball.r < paddle.y + paddle.h && Math.abs(ball.x - paddle.x) < paddle.w / 2 + ball.r) {
      const k = (ball.x - paddle.x) / (paddle.w / 2), sp = Math.hypot(ball.vx, ball.vy) * 1.01;   // where it hits sets the angle
      ball.vx = Math.sin(k * 1.1) * sp; ball.vy = -Math.cos(k * 1.1) * sp; ball.y = paddle.y - ball.r; beep(300, 0.05);
    }
    for (const b of bricks) {
      if (!b.alive || ball.x + ball.r < b.x || ball.x - ball.r > b.x + b.w || ball.y + ball.r < b.y || ball.y - ball.r > b.y + b.h) continue;
      b.alive = false; score += 10 * level; beep(600 + b.hue, 0.05);
      const fromSide = Math.min(ball.x + ball.r - b.x, b.x + b.w - (ball.x - ball.r)) < Math.min(ball.y + ball.r - b.y, b.y + b.h - (ball.y - ball.r));
      if (fromSide) ball.vx *= -1; else ball.vy *= -1;
      for (let i = 0; i < 8; i++) sparks.push({ x: b.x + b.w / 2, y: b.y + b.h / 2, vx: (Math.random() - 0.5) * 260, vy: (Math.random() - 0.5) * 260, life: 0.5, hue: b.hue });
      break;
    }
  }
  if (bricks.every((b) => !b.alive)) { level++; buildBricks(); resetBall(); }
  if (ball.y > H + 20) {
    lives--; shake = 0.25; beep(120, 0.3);
    if (lives <= 0) { mode = 'over'; overAt = performance.now(); if (score > best) { best = score; try { localStorage.setItem('breakout-best', String(best)); } catch (e) { /* ignore */ } } }
    else resetBall();
  }
}
function draw() {
  ctx.save();
  ctx.clearRect(0, 0, W, H);
  if (shake > 0) ctx.translate((Math.random() - 0.5) * shake * 30, (Math.random() - 0.5) * shake * 30);
  for (const b of bricks) if (b.alive) { ctx.fillStyle = 'hsl(' + b.hue + ' 80% 60%)'; ctx.fillRect(b.x + 1, b.y + 1, b.w - 2, b.h - 2); }
  ctx.fillStyle = '#e8f1ff'; ctx.fillRect(paddle.x - paddle.w / 2, paddle.y, paddle.w, paddle.h);
  ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2); ctx.fill();
  for (const p of sparks) { ctx.globalAlpha = Math.max(0, p.life * 2); ctx.fillStyle = 'hsl(' + p.hue + ' 90% 65%)'; ctx.fillRect(p.x, p.y, 4, 4); }
  ctx.globalAlpha = 1; ctx.fillStyle = '#fff'; ctx.font = '700 18px system-ui'; ctx.textAlign = 'left';
  ctx.fillText('점수 ' + score + '  레벨 ' + level + '  목숨 ' + '♥'.repeat(Math.max(0, lives)), 14, 30);
  ctx.textAlign = 'right'; ctx.fillText('최고 ' + best, W - 14, 30); ctx.textAlign = 'center';
  const msg = { ready: ['벽돌깨기', '←→ 또는 마우스/터치로 패들 이동 · 스페이스/탭으로 시작'], over: ['게임 오버', '점수 ' + score + ' · 스페이스 또는 탭으로 다시 시작'] }[mode];
  if (msg) { ctx.fillStyle = '#000a'; ctx.fillRect(0, 250, W, 120); ctx.fillStyle = '#fff'; ctx.font = '700 32px system-ui'; ctx.fillText(msg[0], W / 2, 300); ctx.font = '500 15px system-ui'; ctx.fillText(msg[1], W / 2, 336); }
  else if (ball.stuck) { ctx.font = '500 15px system-ui'; ctx.fillText('스페이스 또는 탭으로 발사', W / 2, H - 100); }
  ctx.restore();
}
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min((now - last) / 1000, 0.1); last = now; acc += dt;
  while (acc >= 1 / 120) { update(1 / 120); acc -= 1 / 120; }
  for (let i = sparks.length - 1; i >= 0; i--) { const p = sparks[i]; p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; if (p.life <= 0) sparks.splice(i, 1); }
  shake = Math.max(0, shake - dt);
  draw();
}
buildBricks(); resetBall();
requestAnimationFrame((t) => { last = t; frame(t); });
window.__game = { get mode() { return mode; }, get score() { return score; }, get lives() { return lives; }, get level() { return level; }, get bricks() { return bricks; }, paddle, ball, press, W };   // test hook
</script>
</body>
</html>
```
