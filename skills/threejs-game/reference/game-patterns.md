---
name: game-patterns
description: Copy-paste three.js game building blocks - object pooling, distance spawner, AABB collision, camera shake, touch buttons, best score, WebAudio beeps, pause, lanes, bullets and enemy chase.
triggers: [pooling, spawner, spawn, collision, aabb, camera shake, touch controls, virtual button, high score, localstorage, sound, beep, pause, lanes, bullets, projectile, enemy ai, chase, 풀링, 스폰, 충돌, 화면 흔들림, 터치, 최고 점수, 효과음, 일시정지, 총알, 적 ai]
---
# Game patterns (three.js r160)

## Object pool (no per-spawn allocation)
```js
class Pool {
  constructor(make, size) { this.items = Array.from({ length: size }, make); this.items.forEach((o) => { o.visible = false; }); }
  get() { const o = this.items.find((x) => !x.visible); if (o) o.visible = true; return o; }
  release(o) { o.visible = false; }
}
const bullets = new Pool(() => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.15, 8, 8), new THREE.MeshBasicMaterial({ color: 0xffe066 })); scene.add(m); return m; }, 30);
```

## Distance-based spawner (fair gaps at every speed)
```js
// fragment
let sinceSpawn = 0, nextGap = 20;
function spawnIfNeeded(dt) {
  sinceSpawn += state.speed * dt;
  if (sinceSpawn < nextGap) return;
  spawnObstacle();
  sinceSpawn = 0;
  nextGap = state.speed * 0.9 + 4 + Math.random() * 12;   // always more than one jump apart
}
```

## Box collision (shrunk, vertical + horizontal)
```js
function overlaps(a, b, shrink = 0.85) {   // a, b = { x, y, w, h }  (x = centre, y = bottom)
  return Math.abs(a.x - b.x) < (a.w + b.w) / 2 * shrink && a.y < b.y + b.h * shrink && a.y + a.h * shrink > b.y;
}
const box = new THREE.Box3(), box2 = new THREE.Box3();
function meshesHit(m1, m2) { box.setFromObject(m1); box2.setFromObject(m2); return box.intersectsBox(box2); }
```
`Box3.setFromObject` also works on Groups but allocates nothing only if you reuse the boxes (as above).

## Camera shake and smooth follow
```js
// fragment
let shake = 0;   // set shake = 0.6 on a hit
function updateCamera(dt) {
  shake = Math.max(0, shake - dt);
  camera.position.x += (player.position.x + 3 - camera.position.x) * (1 - Math.exp(-5 * dt));
  camera.position.y = 3.8 + (Math.random() - 0.5) * shake;
  camera.lookAt(camera.position.x, 1.9, 0);
}
```

## Best score, pause, tiny sound
```js
let best = Number(localStorage.getItem('game-best') || 0);
function saveBest() { best = Math.max(best, Math.floor(state.score)); localStorage.setItem('game-best', String(best)); }
document.addEventListener('visibilitychange', () => { if (document.hidden && state.mode === 'playing') state.mode = 'paused'; });
let audio;
function beep(freq, len) {
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = freq; g.gain.value = 0.05;
    o.connect(g); g.connect(audio.destination);
    o.start(); o.stop(audio.currentTime + len);
  } catch (err) { /* sound is optional; browsers need a click first */ }
}
```
Call `beep(520, 0.08)` on jump, `beep(140, 0.35)` on death.

## Touch buttons (HTML over the canvas)
```html
<div id="pad" style="position:fixed;inset:auto 0 24px 0;display:flex;justify-content:space-between;padding:0 24px;pointer-events:none">
  <button id="btnLeft" style="pointer-events:auto;width:84px;height:84px;border-radius:50%;font-size:32px">◀</button>
  <button id="btnJump" style="pointer-events:auto;width:84px;height:84px;border-radius:50%;font-size:28px">점프</button>
</div>
<script type="module">
  const held = { left: false };
  const bind = (id, on, off) => { const el = document.getElementById(id); el.addEventListener('pointerdown', (e) => { e.preventDefault(); on(); }); ['pointerup', 'pointerleave', 'pointercancel'].forEach((t) => el.addEventListener(t, off)); };
  bind('btnLeft', () => { held.left = true; }, () => { held.left = false; });
  bind('btnJump', () => { window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' })); }, () => {});
</script>
```

## Shooting with cooldown, enemies that chase
```js
// fragment
let cooldown = 0;
function shoot(dt) {
  cooldown -= dt;
  if (!firing || cooldown > 0) return;
  cooldown = 0.18;
  const b = bullets.get(); if (!b) return;
  b.position.copy(player.position).y += 1;
  b.userData.vel = new THREE.Vector3(Math.sin(player.rotation.y), 0, Math.cos(player.rotation.y)).multiplyScalar(30);
  b.userData.life = 1.2;
}
const dir = new THREE.Vector3();
function chase(enemy, target, speed, dt) {
  dir.subVectors(target.position, enemy.position).setY(0).normalize();
  enemy.position.addScaledVector(dir, speed * dt);
  enemy.lookAt(target.position.x, enemy.position.y, target.position.z);
}
```

## Lanes
```js
// fragment
const LANES = [-2.5, 0, 2.5];
let lane = 1;
window.addEventListener('keydown', (e) => {
  if (e.code === 'ArrowLeft') lane = Math.max(0, lane - 1);
  if (e.code === 'ArrowRight') lane = Math.min(2, lane + 1);
});
// each frame: player.position.x += (LANES[lane] - player.position.x) * (1 - Math.exp(-14 * dt));
```
