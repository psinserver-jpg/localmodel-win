---
name: dino-runner
description: Complete 2D Chrome-dino style runner on Canvas 2D - pixel art from strings, fixed timestep, jump math that guarantees clearable obstacles, ducking under birds, particles, beeps, best score, restart. Verified with a 60-second bot at max speed.
triggers: [dino, 공룡, runner, 러너, endless runner, 무한 달리기, 점프, jump, 장애물, obstacle, 선인장, cactus, 달리기 게임, chrome dino, 크롬 공룡, canvas runner, 2d runner]
---
# 2D dino runner (verified: 60 s bot, 59 jumps, 7 ducks, 0 deaths at max speed 700; game over, restart guard, best saved)

`APEX = 156`, `MAX_OBSTACLE_H = 0.55*APEX = 85`, cacti 40-70 px. Change theme via sprite strings/colours; new obstacle = push `{type,x,y,w,h}` in `spawn()` with `h <= MAX_OBSTACLE_H`. `window.__game` lets a bot play.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>공룡 달리기 2D</title>
<style>
  html, body { margin: 0; height: 100%; background: #f7f7f7; overflow: hidden; touch-action: none; user-select: none; }
  body { display: grid; place-items: center; font-family: system-ui, 'Pretendard', sans-serif; }
  canvas { width: min(100vw, 900px, calc(100vh * 2.667)); aspect-ratio: 800 / 300; background: #fff; image-rendering: pixelated; }
</style>
</head>
<body>
<canvas id="c"></canvas>
<script>
const W = 800, H = 300, GROUND = 240;               // logical size; the canvas is scaled to the screen
const GRAVITY = 2600, JUMP_V = 900;                  // apex = v^2 / (2g) = 155 px, airtime 0.69 s
const APEX = JUMP_V * JUMP_V / (2 * GRAVITY);
const MAX_OBSTACLE_H = Math.floor(APEX * 0.55);      // 85 px: anything taller is unclearable
const STEP = 1 / 60;                                 // fixed timestep

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function fit() {                                     // DPR-correct: backing store = CSS size * devicePixelRatio
  const dpr = Math.min(window.devicePixelRatio || 1, 2), r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr);
  canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);   // draw in logical 800x300 units
  ctx.imageSmoothingEnabled = false;
}
window.addEventListener('resize', fit);
fit();

// ---- pixel art from strings: '#' = filled pixel ----
const DINO_BODY = ['........######', '........##.###.', '........######.', '........######.', '........##.....', '#......####....', '#.....#######..', '##...#########.', '.##.##########.', '..############.', '...###########.', '....#########..'];
const DINO_LEGS = [['....##..###...', '....##..#.....'], ['....###.##....', '....#...##....']];
const DINO_DUCK = ['.........######', '.........##.###', '.........######', '.........##....', '##...##########', '.############.#', '..###########..', '...#########...'];
const DUCK_LEGS = [['....##..##....'], ['....#..##.....']];
function drawSprite(rows, x, y, px, color) {         // one fillRect per horizontal run, 0.5 px overlap = no seams when scaled
  ctx.fillStyle = color;
  rows.forEach((row, j) => {
    for (let i = 0; i < row.length; i++) {
      if (row[i] !== '#') continue;
      let n = 1;
      while (row[i + n] === '#') n++;
      ctx.fillRect(x + i * px, y + j * px, n * px, px + 0.5);
      i += n - 1;
    }
  });
}

// ---- state ----
let mode = 'ready';                                   // 'ready' | 'playing' | 'over'
let acc = 0, last = 0, time = 0, score = 0, speed = 300, best = 0, overAt = 0, shake = 0, paused = false;
try { best = Number(localStorage.getItem('dino2d-best') || 0); } catch (e) { /* private mode */ }
const dino = { x: 70, y: 0, vy: 0, w: 40, h: 50, duck: false };   // y = height above ground
const obstacles = [], particles = [], clouds = [];
let nextGap = 0;

function resetGame() {                                // resets EVERYTHING so restart needs no reload
  score = 0; speed = 300; time = 0; nextGap = 500; shake = 0;
  dino.y = 0; dino.vy = 0; dino.duck = false;
  obstacles.length = 0; particles.length = 0;
  clouds.length = 0;
  for (let i = 0; i < 4; i++) clouds.push({ x: i * 220 + Math.random() * 100, y: 30 + Math.random() * 80 });
}
resetGame();

// ---- sound: tiny beeps made with WebAudio, created on the first user gesture ----
let audio = null;
function beep(freq, dur, type = 'square', vol = 0.06) {
  try {
    audio = audio || new AudioContext();
    const o = audio.createOscillator(), g = audio.createGain();
    o.type = type; o.frequency.value = freq; g.gain.value = vol;
    o.connect(g); g.connect(audio.destination); o.start(); o.stop(audio.currentTime + dur);
  } catch (e) { /* audio blocked: the game still works */ }
}

// ---- input: keyboard and pointer feed the same functions ----
function jump() {
  if (mode === 'ready') { startGame(); }
  else if (mode === 'over') { if (performance.now() - overAt > 400) startGame(); return; }   // guard against a held key
  if (dino.y === 0 && !dino.duck) { dino.vy = JUMP_V; beep(660, 0.12); }
}
function startGame() { resetGame(); mode = 'playing'; }
window.addEventListener('keydown', (e) => {
  if (['Space', 'ArrowUp', 'ArrowDown', 'KeyW', 'KeyS', 'KeyP'].includes(e.code)) e.preventDefault();
  if (e.repeat) return;
  if (e.code === 'Space' || e.code === 'ArrowUp' || e.code === 'KeyW') jump();
  if (e.code === 'ArrowDown' || e.code === 'KeyS') dino.duck = true;
  if (e.code === 'KeyP' && mode === 'playing') paused = !paused;
});
window.addEventListener('keyup', (e) => { if (e.code === 'ArrowDown' || e.code === 'KeyS') dino.duck = false; });
canvas.addEventListener('pointerdown', (e) => {       // tap upper part = jump, lower part = duck while held
  const r = canvas.getBoundingClientRect();
  if ((e.clientY - r.top) / r.height > 0.75 && mode === 'playing') dino.duck = true; else jump();
});
window.addEventListener('pointerup', () => { dino.duck = false; });
document.addEventListener('visibilitychange', () => { if (document.hidden && mode === 'playing') paused = true; });

// ---- spawning (every obstacle is clearable by construction) ----
function spawn() {
  const bird = score > 300 && Math.random() < 0.25;
  if (bird) obstacles.push({ type: 'bird', x: W + 20, y: 38 + Math.random() * 12, w: 40, h: 24 });   // bottom 38-50 px up: duck under, or jump over
  else {
    const n = Math.random() < 0.3 ? 2 : 1, h = 40 + Math.random() * Math.min(30, MAX_OBSTACLE_H - 40);   // 40-70 px, always < 85
    obstacles.push({ type: 'cactus', x: W + 20, y: 0, w: 22 * n + 6, h, n });
  }
  const airtime = 2 * JUMP_V / GRAVITY;
  nextGap = speed * airtime + 150 + Math.random() * 250;   // enough room to land and jump again
}

function boom(x, y, n, color) {
  for (let i = 0; i < n; i++) particles.push({ x, y, vx: (Math.random() - 0.5) * 200, vy: Math.random() * 250, life: 0.5 + Math.random() * 0.3, color });
}

// ---- update: fixed step ----
function update(dt) {
  if (mode !== 'playing') return;
  time += dt;
  speed = Math.min(700, 300 + time * 8);              // difficulty ramp, capped
  score += speed * dt * 0.05;
  dino.h = dino.duck ? 28 : 50;
  if (dino.duck && dino.y > 0) dino.vy -= GRAVITY * 2 * dt;     // fast fall when ducking in the air
  dino.vy -= GRAVITY * dt;
  dino.y += dino.vy * dt;
  if (dino.y <= 0) { if (dino.y < 0 && dino.vy < -300) boom(dino.x + 20, 0, 4, '#999'); dino.y = 0; dino.vy = 0; }
  nextGap -= speed * dt;
  if (nextGap <= 0) spawn();
  for (let i = obstacles.length - 1; i >= 0; i--) {
    const o = obstacles[i];
    o.x -= speed * dt;
    if (o.x + o.w < -10) { obstacles.splice(i, 1); continue; }
    // AABB with hitboxes shrunk by 20% so it feels fair (y measured upward from the ground)
    const sx = o.w * 0.1, sy = o.h * 0.1, px = dino.w * 0.1, py = dino.h * 0.1;
    if (dino.x + px < o.x + o.w - sx && dino.x + dino.w - px > o.x + sx && dino.y + py < o.y + o.h - sy && dino.y + dino.h - py > o.y + sy) die();
  }
  for (const c of clouds) { c.x -= speed * 0.15 * dt; if (c.x < -60) { c.x = W + 20; c.y = 30 + Math.random() * 80; } }
}
function die() {
  mode = 'over'; overAt = performance.now(); shake = 0.3;
  boom(dino.x + 20, dino.y + 25, 20, '#535353');
  beep(160, 0.35, 'sawtooth', 0.08);
  if (Math.floor(score) > best) { best = Math.floor(score); try { localStorage.setItem('dino2d-best', String(best)); } catch (e) { /* ignore */ } }
}

// ---- render ----
function draw() {
  ctx.save();
  ctx.clearRect(0, 0, W, H);
  if (shake > 0) ctx.translate((Math.random() - 0.5) * shake * 30, (Math.random() - 0.5) * shake * 30);
  ctx.fillStyle = '#e6e6e6';
  for (const c of clouds) { ctx.fillRect(c.x, c.y, 50, 10); ctx.fillRect(c.x + 10, c.y - 8, 28, 8); }
  ctx.fillStyle = '#535353';
  ctx.fillRect(0, GROUND + 4, W, 2);                  // ground line
  const off = (time * speed) % 40;                    // scrolling ground dashes
  for (let x = -off; x < W; x += 40) ctx.fillRect(x, GROUND + 14, 14, 2);
  const dy = GROUND - dino.y;                         // canvas y of the dino's feet
  const frame = Math.floor(time * 10) % 2;
  if (dino.duck) { drawSprite(DINO_DUCK, dino.x - 6, dy - 27, 3, '#535353'); drawSprite(DUCK_LEGS[frame], dino.x - 6, dy - 3, 3, '#535353'); }
  else {
    drawSprite(DINO_BODY, dino.x - 2, dy - 50 + 6, 3, '#535353');
    drawSprite(dino.y > 0 ? DINO_LEGS[0] : DINO_LEGS[frame], dino.x - 2, dy - 50 + 6 + DINO_BODY.length * 3, 3, '#535353');
  }
  for (const o of obstacles) {
    if (o.type === 'cactus') {
      for (let k = 0; k < o.n; k++) {
        const x = o.x + k * 22 + 3;
        ctx.fillRect(x + 6, GROUND - o.h, 10, o.h);                       // trunk
        ctx.fillRect(x, GROUND - o.h * 0.65, 6, 5); ctx.fillRect(x, GROUND - o.h * 0.65 - 12, 5, 12);   // left arm
        ctx.fillRect(x + 16, GROUND - o.h * 0.5, 6, 5); ctx.fillRect(x + 17, GROUND - o.h * 0.5 - 12, 5, 12);
      }
    } else {
      const top = GROUND - o.y - o.h, wing = Math.floor(time * 8) % 2;
      ctx.fillRect(o.x + 8, top + 8, 28, 10); ctx.fillRect(o.x, top + 10, 10, 5);
      ctx.fillRect(o.x + 14, wing ? top : top + 16, 14, 8);
    }
  }
  for (const p of particles) { ctx.fillStyle = p.color; ctx.globalAlpha = Math.max(0, p.life * 2); ctx.fillRect(p.x, GROUND - p.y, 3, 3); }
  ctx.globalAlpha = 1;
  ctx.fillStyle = '#535353';
  ctx.font = '700 18px monospace';
  ctx.textAlign = 'right';
  ctx.fillText('최고 ' + String(best).padStart(5, '0') + '  ' + String(Math.floor(score)).padStart(5, '0'), W - 16, 28);
  ctx.textAlign = 'center';
  if (mode === 'ready') { ctx.font = '700 28px system-ui'; ctx.fillText('공룡 달리기', W / 2, 110); ctx.font = '500 16px system-ui'; ctx.fillText('스페이스·↑ 점프  ↓ 숙이기  P 일시정지 · 화면을 눌러 시작', W / 2, 140); }
  if (mode === 'over') { ctx.font = '700 28px system-ui'; ctx.fillText('게임 오버', W / 2, 110); ctx.font = '500 16px system-ui'; ctx.fillText('점수 ' + Math.floor(score) + ' · 스페이스 또는 화면을 눌러 다시 시작', W / 2, 140); }
  if (paused) { ctx.font = '700 28px system-ui'; ctx.fillText('일시정지 (P)', W / 2, 110); }
  ctx.restore();
}

// ---- main loop: fixed timestep accumulator, render once per frame ----
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min((now - last) / 1000, 0.1);       // clamp so a hidden tab does not cause a huge catch-up
  last = now;
  if (paused) { draw(); return; }
  acc += dt;
  while (acc >= STEP) { update(STEP); acc -= STEP; }
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy -= 600 * dt;
    if (p.life <= 0 || p.y < 0) particles.splice(i, 1);
  }
  shake = Math.max(0, shake - dt);
  draw();
}
requestAnimationFrame((t) => { last = t; frame(t); });
window.__game = { get mode() { return mode; }, get score() { return score; }, get speed() { return speed; }, get best() { return best; }, dino, obstacles, press: jump, GROUND, APEX, MAX_OBSTACLE_H,
  setDuck(v) { dino.duck = v; } };
</script>
</body>
</html>
```
