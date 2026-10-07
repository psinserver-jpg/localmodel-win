---
name: tilemap-platformer
description: Complete tile-based 2D platformer on Canvas 2D - level from string rows, one-axis tile collision, coyote time, jump buffer, variable jump, patrolling stompable enemies, spikes, coins, flag, scrolling camera, touch zones, lives, best score. Verified: a bot clears it with 0 deaths.
triggers: [platformer, 플랫포머, 플랫폼, tilemap, 타일맵, tile, 타일, 횡스크롤, side scroller, scrolling, 스크롤, 마리오, mario, 코인, coin, 적, enemy, 가시, spikes, camera, 카메라, 레벨, level, 2d game]
---
# Tilemap platformer (verified: bot won with 0 deaths; coins, stomp, game over, restart and best score worked)

Level rules the layout follows (keep them when editing `LEVEL`): apex 128 px = 4 tiles; walls 1 tile; platforms 3 tiles above ground with 64 px clearance below; gaps 3 tiles; hazards >= 9 tiles apart; never a hazard within 6 tiles after a gap or under a platform (jumps bump the ceiling). Ideas: more enemy kinds, moving platforms, checkpoints, particles (see `dino-runner`).

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>타일맵 플랫포머</title>
<style>
  html, body { margin: 0; height: 100%; background: #1b1f33; overflow: hidden; touch-action: none; user-select: none; }
  body { display: grid; place-items: center; font-family: system-ui, 'Pretendard', sans-serif; }
  canvas { width: min(100vw, 960px, calc(100vh * 1.6667)); aspect-ratio: 640 / 384; background: #6ec6ff; image-rendering: pixelated; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const W = 640, H = 384, T = 32;
const LEVEL = [   // '#' ground  '=' platform  'o' coin  'E' enemy  '^' spikes  'F' flag; short rows are padded with air
  '',
  '',
  '',
  '',
  '',
  '                      ooo                            ooo           oo',
  '',
  '                o    =====                     o    =====         ====                 o',
  '    ooo                      o        o                      oo                            F',
  '         E                   #        E                      ^^           E     #          F',
  '###############   ############################   #####################################   #####',
  '###############   ############################   #####################################   #####'
];
const COLS = Math.max(...LEVEL.map((r) => r.length)), ROWS = LEVEL.length;
for (let i = 0; i < ROWS; i++) LEVEL[i] = LEVEL[i].padEnd(COLS);
const GRAVITY = 1500, JUMP_V = 620, RUN = 210;      // apex 128 px = 4 tiles: walls 1 tile, platforms 3 tiles up, gaps 3 tiles

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function fit() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2), r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr);
  canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  ctx.imageSmoothingEnabled = false;
}
window.addEventListener('resize', fit);
fit();

const solid = (c, r) => c < 0 || c >= COLS ? true : r < 0 ? false : r >= ROWS ? false : '#='.includes(LEVEL[r][c]);
const tileAt = (c, r) => (r < 0 || r >= ROWS || c < 0 || c >= COLS ? ' ' : LEVEL[r][c]);

let mode = 'ready', score = 0, lives = 3, best = 0, camX = 0, time = 0, overAt = 0, acc = 0, last = 0;
try { best = Number(localStorage.getItem('plat-best') || 0); } catch (e) { /* ignore */ }
const player = { x: 40, y: 200, w: 22, h: 30, vx: 0, vy: 0, onGround: false, face: 1, coyote: 0, buffer: 0, invul: 0 };
let coins = new Set(), enemies = [];

function loadLevel() {
  coins = new Set(); enemies = [];
  LEVEL.forEach((row, r) => [...row].forEach((ch, c) => {
    if (ch === 'o') coins.add(c + ',' + r);
    if (ch === 'E') enemies.push({ x: c * T + 4, y: r * T + 6, w: 24, h: 26, dir: -1, alive: true, home: c * T + 4 });
  }));
}
function respawn() { Object.assign(player, { x: 40, y: 200, vx: 0, vy: 0, invul: 1.5 }); camX = 0; }
function newGame() { score = 0; lives = 3; time = 0; loadLevel(); respawn(); mode = 'playing'; }

// ---- sound ----
let audio = null;
function beep(f, d, type = 'square') {
  try {
    audio = audio || new AudioContext();
    const o = audio.createOscillator(), g = audio.createGain();
    o.type = type; o.frequency.value = f; g.gain.value = 0.05;
    o.connect(g); g.connect(audio.destination); o.start(); o.stop(audio.currentTime + d);
  } catch (e) { /* audio blocked */ }
}

// ---- input: held state for left/right/jump, from keyboard and touch buttons ----
const held = { left: false, right: false, jump: false };
const KEYMAP = { ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ArrowUp: 'jump', KeyW: 'jump', Space: 'jump' };
function setKey(k, down) {
  if (k === 'jump' && down && !held.jump) {
    if (mode === 'ready') newGame();
    else if (mode !== 'playing' && performance.now() - overAt > 500) newGame();
    player.buffer = 0.12;                              // jump buffer
  }
  held[k] = down;
}
window.addEventListener('keydown', (e) => { if (KEYMAP[e.code]) { e.preventDefault(); setKey(KEYMAP[e.code], true); } });
window.addEventListener('keyup', (e) => { if (KEYMAP[e.code]) setKey(KEYMAP[e.code], false); });
window.addEventListener('blur', () => { held.left = held.right = held.jump = false; });
// touch: left quarter = left, second quarter = right, right half = jump (multi-touch works through pointer ids)
const zone = (e) => { const x = (e.clientX - canvas.getBoundingClientRect().left) / canvas.clientWidth; return x < 0.25 ? 'left' : x < 0.5 ? 'right' : 'jump'; };
const touches = new Map();
canvas.addEventListener('pointerdown', (e) => {
  if (mode !== 'playing') { setKey('jump', true); setKey('jump', false); return; }
  const k = zone(e); touches.set(e.pointerId, k); setKey(k, true);
});
['pointerup', 'pointercancel'].forEach((n) => window.addEventListener(n, (e) => { const k = touches.get(e.pointerId); if (k) { setKey(k, false); touches.delete(e.pointerId); } }));

// ---- physics: move one axis at a time against the tile grid ----
function moveAxis(e, dx, dy) {
  e.x += dx; e.y += dy;
  const c0 = Math.floor(e.x / T), c1 = Math.floor((e.x + e.w - 0.01) / T), r0 = Math.floor(e.y / T), r1 = Math.floor((e.y + e.h - 0.01) / T);
  let hit = false;
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) {
    if (!solid(c, r)) continue;
    hit = true;
    if (dx > 0) e.x = c * T - e.w; else if (dx < 0) e.x = (c + 1) * T;
    if (dy > 0) { e.y = r * T - e.h; e.onGround = true; } else if (dy < 0) e.y = (r + 1) * T;
  }
  return hit;
}
function hurt() {
  if (player.invul > 0) return;
  lives--; beep(140, 0.4, 'sawtooth');
  if (lives <= 0) { mode = 'over'; overAt = performance.now(); } else respawn();
}

function update(dt) {
  if (mode !== 'playing') return;
  time += dt; player.invul = Math.max(0, player.invul - dt);
  const dir = (held.right ? 1 : 0) - (held.left ? 1 : 0);
  const target = dir * RUN, accel = player.onGround ? 2200 : 1400;
  player.vx += Math.sign(target - player.vx) * Math.min(Math.abs(target - player.vx), accel * dt);
  if (dir) player.face = dir;
  player.coyote = player.onGround ? 0.1 : player.coyote - dt;   // coyote time
  player.buffer -= dt;
  if (player.buffer > 0 && player.coyote > 0) { player.vy = -JUMP_V; player.coyote = 0; player.buffer = 0; beep(520, 0.1); }
  if (!held.jump && player.vy < -200) player.vy = -200;           // short hop
  player.vy = Math.min(player.vy + GRAVITY * dt, 900);
  player.onGround = false;
  moveAxis(player, player.vx * dt, 0);
  if (moveAxis(player, 0, player.vy * dt)) player.vy = 0;       
  if (player.y > ROWS * T + 100) hurt();
  const pc = Math.floor((player.x + player.w / 2) / T), pr = Math.floor((player.y + player.h / 2) / T);
  if (coins.delete(pc + ',' + pr)) { score += 10; beep(880, 0.08, 'triangle'); }
  const t = tileAt(pc, Math.floor((player.y + player.h - 2) / T));
  if (t === '^' && player.y + player.h > Math.floor((player.y + player.h - 2) / T) * T + 14) hurt();   // tips only
  if (t === 'F') { score += Math.max(0, 300 - Math.floor(time) * 5); mode = 'won'; overAt = performance.now(); beep(988, 0.4, 'triangle'); }
  for (const en of enemies) {
    if (!en.alive) continue;
    en.x += en.dir * 60 * dt;
    const ahead = Math.floor((en.x + (en.dir > 0 ? en.w : 0)) / T), below = Math.floor((en.y + en.h + 2) / T);
    if (solid(ahead, Math.floor(en.y / T)) || !solid(ahead, below) || Math.abs(en.x - en.home) > 80) en.dir = en.x > en.home ? -1 : 1;   // patrol
    if (player.x < en.x + en.w && player.x + player.w > en.x && player.y < en.y + en.h && player.y + player.h > en.y) {
      if (player.vy > 0 && player.y + player.h < en.y + en.h * 0.6) { en.alive = false; player.vy = -380; score += 50; beep(300, 0.15); }
      else hurt();
    }
  }
  camX += (Math.max(0, Math.min(COLS * T - W, player.x - W / 2 + 40)) - camX) * (1 - Math.exp(-8 * dt));
}

function draw() {
  ctx.fillStyle = '#6ec6ff'; ctx.fillRect(0, 0, W, H);
  ctx.save();
  ctx.translate(-Math.round(camX), 0);
  const c0 = Math.max(0, Math.floor(camX / T)), c1 = Math.min(COLS - 1, Math.ceil((camX + W) / T));
  for (let r = 0; r < ROWS; r++) for (let c = c0; c <= c1; c++) {
    const ch = LEVEL[r][c], x = c * T, y = r * T;
    if (ch === '#') { ctx.fillStyle = solid(c, r - 1) ? '#8d5a3b' : '#4caf50'; ctx.fillRect(x, y, T, T); }
    else if (ch === '=') { ctx.fillStyle = '#b07b4f'; ctx.fillRect(x, y, T, 12); }
    else if (ch === '^') { ctx.fillStyle = '#cfd8dc'; for (let k = 0; k < 2; k++) { ctx.beginPath(); ctx.moveTo(x + k * 16, y + T); ctx.lineTo(x + k * 16 + 8, y + 12); ctx.lineTo(x + k * 16 + 16, y + T); ctx.fill(); } }
    else if (ch === 'F') { ctx.fillStyle = '#eceff1'; ctx.fillRect(x + 14, y, 4, T); if (LEVEL[r - 1][c] !== 'F') { ctx.fillStyle = '#ff5252'; ctx.fillRect(x + 18, y + 2, 18, 12); } }
  }
  const bob = Math.sin(time * 6) * 2;               
  ctx.fillStyle = '#ffd54f';
  for (const key of coins) { const [c, r] = key.split(',').map(Number); ctx.beginPath(); ctx.arc(c * T + 16, r * T + 16 + bob, 7, 0, 7); ctx.fill(); }
  for (const en of enemies) if (en.alive) { ctx.fillStyle = '#8d4a3a'; ctx.fillRect(en.x, en.y, en.w, en.h); ctx.fillStyle = '#fff'; ctx.fillRect(en.x + 5, en.y + 6, 14, 6); }
  if (player.invul <= 0 || Math.floor(time * 20) % 2) {
    ctx.fillStyle = '#e53935'; ctx.fillRect(player.x, player.y, player.w, player.h);
    ctx.fillStyle = '#ffccbc'; ctx.fillRect(player.x + (player.face > 0 ? 10 : 2), player.y + 4, 10, 8);
    ctx.fillStyle = '#1565c0'; ctx.fillRect(player.x + 2, player.y + 20, player.w - 4, 10);
  }
  ctx.restore();
  ctx.fillStyle = '#fff'; ctx.font = '700 18px system-ui'; ctx.textAlign = 'left';
  ctx.fillText('점수 ' + score + '   목숨 ' + '♥'.repeat(Math.max(0, lives)) + '   최고 ' + best, 12, 26);
  ctx.textAlign = 'center'; ctx.font = '700 30px system-ui';
  const again = '점수 ' + score + ' · 스페이스 또는 화면을 눌러 다시 시작';
  const msg = { ready: ['타일맵 플랫포머', '← → 이동 · 스페이스 점프 · 적은 밟기 · 깃발까지 (터치: 왼쪽 이동, 오른쪽 점프)'], over: ['게임 오버', again], won: ['클리어!', again] }[mode];
  if (msg) { ctx.fillStyle = '#000a'; ctx.fillRect(0, 100, W, 110); ctx.fillStyle = '#fff'; ctx.fillText(msg[0], W / 2, 150); ctx.font = '500 16px system-ui'; ctx.fillText(msg[1], W / 2, 184); }
}

function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min((now - last) / 1000, 0.1); last = now;
  acc += dt;
  while (acc >= 1 / 60) { update(1 / 60); acc -= 1 / 60; }
  if ((mode === 'won' || mode === 'over') && score > best) { best = score; try { localStorage.setItem('plat-best', String(best)); } catch (e) { /* ignore */ } }
  draw();
}
loadLevel();
requestAnimationFrame((t) => { last = t; frame(t); });
window.__game = { get mode() { return mode; }, get score() { return score; }, get lives() { return lives; }, player, enemies, T, solid, tileAt, held, setKey, get coinsLeft() { return coins.size; }, COLS };
</script>
</body>
</html>
```
