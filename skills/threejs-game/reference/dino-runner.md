---
name: dino-runner
description: Complete, tested 3D endless-runner (Chrome dino style) in one HTML file - low-poly dino, cacti and birds, jump and duck, speed ramp, score and high score, game over and restart, touch controls. Copy it and change the theme or rules.
triggers: [dino, dinosaur, runner, endless runner, infinite runner, chrome dino, jump game, obstacle game, 공룡, 공룡게임, 공룡 게임, 러너, 무한 달리기, 달리기 게임, 점프 게임, 장애물, 선인장, 크롬 공룡]
---
# Dino runner - full working game (three.js r160, single file)

Verified in a real browser: it starts, spawns cacti and birds, a bot that jumps and ducks survives 45 s while the speed ramps from 12 to 22, dying shows the Korean game-over screen, a press right after dying is ignored (0.4 s guard), the next press restarts with score 0 and the best score saved.

How to adapt: change the colors/meshes (`makeCactus`, `makeBird`, the dino parts), the texts, the spawn rules in `spawn()`, the physics constants at the top. Keep the structure (state machine, `update(dt)`, `startGame/endGame`) and keep every obstacle clearable (see the fairness rules in the skill).

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>3D 공룡 달리기</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #dff3ff; touch-action: none; user-select: none; }
  canvas { display: block; }
  #hud { position: fixed; inset: 0; pointer-events: none; font: 700 22px/1.4 'Pretendard', system-ui, sans-serif; color: #2b2b2b; }
  #score { position: absolute; top: 16px; right: 20px; letter-spacing: 2px; }
  #msg { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; gap: 8px; }
  #msg h1 { margin: 0; font-size: clamp(28px, 6vw, 56px); }
  #msg p { margin: 0; font-weight: 500; opacity: .75; }
  #msg.hide { display: none; }
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
</head>
<body>
<div id="hud">
  <div id="score">최고 00000 &nbsp; 00000</div>
  <div id="msg"><h1>공룡 달리기 3D</h1><p>스페이스·↑ 점프 | ↓ 숙이기 | 터치로 점프</p><p>눌러서 시작</p></div>
</div>
<script type="module">
import * as THREE from 'three';

const DINO_X = -3, GRAVITY = -45, JUMP_V = 17, MAX_SPEED = 28;   // apex 3.2 m
let state = 'ready', speed = 12, score = 0, vy = 0, ducking = false, distSinceSpawn = 0, nextGap = 20, shake = 0, overAt = 0;
let best = Number(localStorage.getItem('dino3d-best') || 0);
const obstacles = [];
const $ = (id) => document.getElementById(id);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdff3ff);
scene.fog = new THREE.Fog(0xdff3ff, 30, 80);
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);

scene.add(new THREE.HemisphereLight(0xffffff, 0xb8a47a, 1.1));
const sun = new THREE.DirectionalLight(0xfff2d6, 2.2);
sun.position.set(-6, 14, 10);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -20, right: 20, top: 12, bottom: -12, near: 1, far: 40 });
scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(260, 24), new THREE.MeshStandardMaterial({ color: 0xe8dcb8 }));
ground.rotation.x = -Math.PI / 2;
ground.position.x = 40;
ground.receiveShadow = true;
scene.add(ground);

const dashMat = new THREE.MeshStandardMaterial({ color: 0xb9a878 });
const dashes = [];
for (let i = 0; i < 20; i++) {
  const d = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.02, 0.12), dashMat);
  d.position.set(-20 + i * 4.5, 0.01, 1.6 + (i % 3) * 1.2);
  scene.add(d);
  dashes.push(d);
}
const hills = [];
for (let i = 0; i < 8; i++) {
  const h = new THREE.Mesh(new THREE.ConeGeometry(6 + (i % 3) * 2, 5 + (i % 4), 5), new THREE.MeshStandardMaterial({ color: 0xa8c8a0, flatShading: true }));
  h.position.set(-30 + i * 14, 2, -16);
  scene.add(h);
  hills.push(h);
}
const clouds = [];
for (let i = 0; i < 7; i++) {
  const c = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color: 0xffffff, flatShading: true });
  for (let k = 0; k < 3; k++) {
    const s = new THREE.Mesh(new THREE.IcosahedronGeometry(1 + k * 0.2, 0), m);
    s.position.set(k * 1.3, (k % 2) * 0.3, 0);
    c.add(s);
  }
  c.position.set(-25 + i * 12, 6 + (i % 3) * 1.2, -9 - (i % 2) * 4);
  scene.add(c);
  clouds.push(c);
}
const dino = new THREE.Group();
const green = new THREE.MeshStandardMaterial({ color: 0x58a55c, flatShading: true });
const belly = new THREE.MeshStandardMaterial({ color: 0xcfe8b8, flatShading: true });
function part(w, h, d, mat, x, y, z, parent = dino) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = true;
  parent.add(m);
  return m;
}
part(1.8, 1.4, 1.1, green, 0, 1.55, 0);          // body
part(1.2, 0.6, 1.0, belly, 0.25, 1.15, 0);        // belly
part(0.8, 1.0, 0.8, green, 0.9, 2.35, 0);         // neck
part(1.3, 0.9, 0.95, green, 1.35, 2.95, 0);       // head
part(0.5, 0.3, 0.8, belly, 2.0, 2.7, 0);          // jaw
part(0.18, 0.18, 0.1, new THREE.MeshStandardMaterial({ color: 0x111111 }), 1.55, 3.2, 0.5);  // eye
part(1.2, 0.8, 0.8, green, -1.4, 1.7, 0).rotation.z = 0.25;   // tail 1
part(0.9, 0.5, 0.6, green, -2.2, 1.95, 0).rotation.z = 0.4;    // tail 2
const legs = [-0.35, 0.45].map((x) => {
  const pivot = new THREE.Group();
  pivot.position.set(x, 0.9, 0);
  part(0.5, 0.9, 0.45, green, 0, -0.45, x < 0 ? 0.28 : -0.28, pivot);
  dino.add(pivot);
  return pivot;
});
dino.position.set(DINO_X, 0, 0);
scene.add(dino);
const cactusMat = new THREE.MeshStandardMaterial({ color: 0x2e7d32, flatShading: true });
function makeCactus() {
  const g = new THREE.Group();
  const count = 1 + Math.floor(Math.random() * 3);
  let width = 0, height = 0;
  for (let i = 0; i < count; i++) {
    const h = 1.2 + Math.random() * 0.8;   // far below the jump apex
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.35, h, 8), cactusMat);
    stem.position.set(i * 0.95, h / 2, 0);
    stem.castShadow = true;
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.25, 0.25), cactusMat);
    arm.position.set(i * 0.95 + 0.4, h * 0.6, 0);
    arm.castShadow = true;
    g.add(stem, arm);
    width = i * 0.95 + 0.7;
    height = Math.max(height, h);
  }
  return { mesh: g, w: width, h: height, y: 0, bird: false };
}
function makeBird() {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0x6d4c41, flatShading: true });
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.5, 0.6), mat);
  const beak = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.6, 4), new THREE.MeshStandardMaterial({ color: 0xffb300 }));
  beak.rotation.z = Math.PI / 2;
  beak.position.set(-0.95, 0, 0);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.08, 1.6), mat);
  wing.position.set(0, 0.2, 0);
  g.add(body, beak, wing);
  g.traverse((o) => { o.castShadow = true; });
  g.position.y = 2.1;
  return { mesh: g, w: 1.4, h: 0.6, y: 1.8, bird: true };
}
function spawn() {
  const o = Math.random() < 0.28 && score > 150 ? makeBird() : makeCactus();
  o.mesh.position.x = 34;
  if (o.bird) o.mesh.position.y = 2.1;
  scene.add(o.mesh);
  obstacles.push(o);
  nextGap = speed * 0.9 + 4 + Math.random() * 12;
  distSinceSpawn = 0;
}
function jump() { if (dino.position.y <= 0.001 && !ducking) { vy = JUMP_V; } }
function press() {
  if (state === 'ready' || (state === 'over' && performance.now() - overAt > 400)) startGame();
  else if (state === 'playing') jump();
}
window.addEventListener('keydown', (e) => {
  if (['Space', 'ArrowUp', 'KeyW'].includes(e.code)) { e.preventDefault(); if (!e.repeat) press(); }
  if (['ArrowDown', 'KeyS'].includes(e.code)) { e.preventDefault(); ducking = true; }
});
window.addEventListener('keyup', (e) => { if (['ArrowDown', 'KeyS'].includes(e.code)) ducking = false; });
renderer.domElement.addEventListener('pointerdown', (e) => {
  if (state === 'playing' && e.clientY > window.innerHeight * 0.75) ducking = true; else press();
});
window.addEventListener('pointerup', () => { ducking = false; });
$('msg').addEventListener('pointerdown', press);
document.addEventListener('visibilitychange', () => { if (document.hidden && state === 'playing') endGame(); });

function startGame() {
  obstacles.splice(0).forEach((o) => scene.remove(o.mesh));
  state = 'playing'; speed = 12; score = 0; vy = 0; ducking = false; distSinceSpawn = 0; nextGap = 20;
  dino.position.y = 0;
  $('msg').classList.add('hide');
}
function endGame() {
  state = 'over'; overAt = performance.now(); shake = 0.6;
  best = Math.max(best, Math.floor(score));
  localStorage.setItem('dino3d-best', String(best));
  $('msg').innerHTML = '<h1>게임 오버</h1><p>점수 ' + Math.floor(score) + ' · 최고 ' + best + '</p><p>스페이스바 또는 화면을 눌러 다시 시작</p>';
  $('msg').classList.remove('hide');
}
function hits(o) {
  const dh = ducking && dino.position.y <= 0.001 ? 1.3 : 2.4;
  const dx = Math.abs(o.mesh.position.x + (o.bird ? 0 : o.w / 2 - 0.35) - (DINO_X + 0.2));
  const overlapX = dx < (o.w + 1.5) / 2 * 0.8;
  const dBottom = dino.position.y, dTop = dino.position.y + dh;
  const oBottom = o.y, oTop = o.y + o.h;
  return overlapX && dBottom < oTop * 0.9 && dTop * 0.92 > oBottom;
}

const clock = new THREE.Clock();
function update(dt, t) {
  if (state === 'playing') {
    speed = Math.min(MAX_SPEED, speed + dt * 0.25);
    score += speed * dt * 0.8;
    vy += GRAVITY * dt * (ducking && dino.position.y > 0 ? 2.2 : 1);
    dino.position.y = Math.max(0, dino.position.y + vy * dt);
    if (dino.position.y === 0) vy = 0;
    dino.scale.y = ducking && dino.position.y === 0 ? 0.55 : 1;
    distSinceSpawn += speed * dt;
    if (distSinceSpawn > nextGap) spawn();
    for (let i = obstacles.length - 1; i >= 0; i--) {
      const o = obstacles[i];
      o.mesh.position.x -= speed * dt;
      if (o.bird) o.mesh.rotation.z = Math.sin(t * 18) * 0.12;
      if (hits(o)) endGame();
      else if (o.mesh.position.x < -30) { scene.remove(o.mesh); obstacles.splice(i, 1); }
    }
    const swing = Math.sin(t * speed * 0.9) * 0.9;
    legs[0].rotation.z = dino.position.y > 0 ? 0.5 : swing;
    legs[1].rotation.z = dino.position.y > 0 ? -0.5 : -swing;
    $('score').innerHTML = '최고 ' + String(best).padStart(5, '0') + ' &nbsp; ' + String(Math.floor(score)).padStart(5, '0');
  }
  const scroll = state === 'playing' ? speed : 3;
  dashes.forEach((d) => { d.position.x -= scroll * dt; if (d.position.x < -22) d.position.x += 90; });
  hills.forEach((h) => { h.position.x -= scroll * dt * 0.15; if (h.position.x < -35) h.position.x += 112; });
  clouds.forEach((c) => { c.position.x -= scroll * dt * 0.3; if (c.position.x < -30) c.position.x += 84; });
}

function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;
  update(dt, t);
  shake = Math.max(0, shake - dt);
  camera.position.set(3.5 + (Math.random() - 0.5) * shake, 3.8 + (Math.random() - 0.5) * shake, 14.5);
  camera.lookAt(3.5, 1.9, 0);
  renderer.render(scene, camera);
}
function onResize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  camera.fov = w / h < 1 ? 78 : 50;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}
window.addEventListener('resize', onResize);
onResize();
frame();
</script>
</body>
</html>
```
