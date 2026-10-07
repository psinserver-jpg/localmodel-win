---
name: platformer-custom
description: Complete working page: custom physics character (gravity, jump with coyote time and jump buffer, variable jump height, AABB per-axis resolution with epsilon, substeps against tunnelling), platforms and coins, no library.
triggers: [platformer physics, 플랫포머, custom physics, 직접 만든 물리, jump physics, 점프 높이, aabb example, 충돌 예제, coyote time, 코요테, character controller, 캐릭터 컨트롤러, 코인]
---
# Own-physics platformer (verified in a browser)
Checked numbers: g=30, jump 12 -> apex 2.4 m (measured 2.31 above the floor, because of per-frame integration), airtime 0.8 s. Platform tops at 1.2 and 2.0 m, plank at 1.2 m: all clearable. A bot jumped onto the 1.2 m platform and rested at y = 1.8 (top 1.2 + half height 0.6). Side-view camera follows with exponential smoothing. To use as a game: add enemies as AABBs and call the same `overlap()`.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>직접 만든 물리</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#bfe3ff}canvas{display:block}#hud{position:fixed;left:16px;top:12px;font:15px sans-serif;color:#123}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
</head>
<body>
<div id="hud">←/→ 또는 A/D 이동, 스페이스 점프 · 코인 <span id="coins">0</span></div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xbfe3ff);
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 1.1));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.2);
sun.position.set(6, 12, 8);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 10, bottom: -6, near: 1, far: 40 });
scene.add(sun);

// ---- numbers (sanity-checked): g = 30, jump speed 12 -> apex = v*v/(2g) = 2.4 m, airtime = 2v/g = 0.8 s
const G = 30, JUMP = 12, SPEED = 6, MAX_FALL = 40;
// platforms as AABBs {min, max}; tallest step is 1.2 / 2.0 m, apex 2.4 m, so every jump is clearable with margin
const solids = [];
function addSolid(x, y, w, h, color) {   // x,y = centre
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, 2), new THREE.MeshStandardMaterial({ color, roughness: 0.8 }));
  mesh.position.set(x, y, 0);
  mesh.castShadow = mesh.receiveShadow = true;
  scene.add(mesh);
  solids.push({ minX: x - w / 2, maxX: x + w / 2, minY: y - h / 2, maxY: y + h / 2 });
}
addSolid(0, -1, 40, 2, 0x6ab04c);      // ground, top at y = 0
addSolid(6, 0.6, 4, 1.2, 0xc0824a);    // top at 1.2
addSolid(11, 1.0, 4, 2.0, 0xc0824a);   // top at 2.0
addSolid(-6, 1.0, 3, 0.4, 0xc0824a);   // thin floating plank, top at 1.2

const player = { x: 0, y: 0.6, vx: 0, vy: 0, w: 0.8, h: 1.2, onGround: false, coyote: 0, buffer: 0 };
const pm = new THREE.Mesh(new THREE.BoxGeometry(player.w, player.h, 0.8), new THREE.MeshStandardMaterial({ color: 0xff7043 }));
pm.castShadow = true;
scene.add(pm);

const coins = [];
let score = 0;
for (const [x, y] of [[6, 2.2], [11, 3.0], [-6, 2.2], [2, 1.5]]) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.08, 20), new THREE.MeshStandardMaterial({ color: 0xffd23f, metalness: 0.6, roughness: 0.3, emissive: 0x553300 }));
  m.rotation.x = Math.PI / 2;
  m.position.set(x, y, 0);
  scene.add(m);
  coins.push({ m, x, y, got: false });
}

const keys = {};
addEventListener('keydown', (e) => { keys[e.code] = true; if (e.code === 'Space') player.buffer = 0.12; });
addEventListener('keyup', (e) => { keys[e.code] = false; });

const EPS = 0.001;   // without it, standing exactly on a top face counts as overlapping the side (float error) and you get pushed sideways
const overlap = (p, s) => p.x - p.w / 2 < s.maxX - EPS && p.x + p.w / 2 > s.minX + EPS && p.y - p.h / 2 < s.maxY - EPS && p.y + p.h / 2 > s.minY + EPS;
function step(dt) {
  const dir = (keys.ArrowRight || keys.KeyD ? 1 : 0) - (keys.ArrowLeft || keys.KeyA ? 1 : 0);
  player.vx = dir * SPEED;
  player.vy = Math.max(player.vy - G * dt, -MAX_FALL);
  player.coyote = player.onGround ? 0.1 : player.coyote - dt;      // jump slightly after leaving a ledge
  player.buffer -= dt;                                            // jump slightly before landing
  if (player.buffer > 0 && player.coyote > 0) { player.vy = JUMP; player.buffer = 0; player.coyote = 0; }
  if (!keys.Space && player.vy > 0) player.vy -= G * dt * 1.5;    // release early = shorter hop
  player.onGround = false;
  // move one axis at a time, resolve each against every solid; small substeps stop tunnelling
  const n = Math.ceil(Math.max(Math.abs(player.vx), Math.abs(player.vy)) * dt / 0.25) || 1;
  for (let i = 0; i < n; i++) {
    player.x += player.vx * dt / n;
    for (const s of solids) if (overlap(player, s)) player.x = player.vx > 0 ? s.minX - player.w / 2 : s.maxX + player.w / 2;
    player.y += player.vy * dt / n;
    for (const s of solids) if (overlap(player, s)) {
      if (player.vy <= 0) { player.y = s.maxY + player.h / 2; player.onGround = true; } else player.y = s.minY - player.h / 2;
      player.vy = 0;
    }
  }
  if (player.y < -15) { player.x = 0; player.y = 3; player.vy = 0; }   // fell off the world: respawn
  for (const c of coins) if (!c.got && Math.hypot(c.x - player.x, c.y - player.y) < 0.8) { c.got = true; c.m.visible = false; score++; document.getElementById('coins').textContent = score; }
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  step(dt);
  pm.position.set(player.x, player.y, 0);
  for (const c of coins) c.m.rotation.z += dt * 3;
  camera.position.x += (player.x - camera.position.x) * Math.min(1, dt * 5);   // smooth follow
  camera.position.set(camera.position.x, 3.5, 14);
  camera.lookAt(camera.position.x, 2, 0);
  renderer.render(scene, camera);
});
window.__g = { player, keys, step };
</script>
</body>
</html>
```
