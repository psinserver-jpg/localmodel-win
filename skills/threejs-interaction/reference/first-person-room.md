---
name: first-person-room
description: First-person room with PointerLockControls, WASD movement with smoothing, head bob, circle-vs-AABB wall sliding and a click-to-start overlay. Verified: walking into a wall stops at the wall.
triggers: [first person, 1인칭, fps, pointerlock, pointer lock, 포인터락, room, 방, 미술관, museum, maze, 미로, collision, 충돌, wasd, walk, 걷기, 시점, 둘러보기]
---
# First-person room (verified: camera walked from z=5 and stopped at z=-5.5 against the wall, no errors)

Add more furniture with `box(w,h,d,x,y,z,material)` - every call is also a collider. Mobile: PointerLock is unavailable, so on touch devices use OrbitControls or add a joystick (see `third-person-walker`) and drag-to-look with `camera.rotation.y -= dx * 0.005` (order `YXZ`).

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>1인칭 방</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#111}canvas{display:block}
#start{position:fixed;inset:0;display:grid;place-content:center;text-align:center;gap:8px;background:#000a;color:#fff;font:600 20px/1.5 system-ui,sans-serif;cursor:pointer}
#start small{font-weight:500;opacity:.8;font-size:15px}
#cross{position:fixed;left:50%;top:50%;width:6px;height:6px;margin:-3px;border-radius:50%;background:#fff;opacity:.8;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="cross"></div>
<div id="start"><div>클릭해서 시작</div><small>WASD 이동 · 마우스로 둘러보기 · Esc 일시정지</small></div>
<script type="module">
import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a22);
const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 60);
camera.position.set(0, 1.7, 5);                               // eye height 1.7 m

const controls = new PointerLockControls(camera, renderer.domElement);
const startEl = document.getElementById('start');
startEl.addEventListener('click', () => controls.lock());
controls.addEventListener('lock', () => { startEl.style.display = 'none'; });
controls.addEventListener('unlock', () => { startEl.style.display = 'grid'; });

// ---- room 12 x 12, height 3.2 ----
const mat = (c, r = 0.9) => new THREE.MeshStandardMaterial({ color: c, roughness: r });
const solids = [];                                             // every collidable AABB: {minX,maxX,minZ,maxZ}
function box(w, h, d, x, y, z, material, solid = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  m.position.set(x, y, z);
  m.castShadow = m.receiveShadow = true;
  scene.add(m);
  if (solid) solids.push({ minX: x - w / 2, maxX: x + w / 2, minZ: z - d / 2, maxZ: z + d / 2 });
  return m;
}
const wallM = mat(0xe9e1d3);
box(12, 0.1, 12, 0, -0.05, 0, mat(0x8a6a4a, 0.6), false);       // floor
box(12, 0.1, 12, 0, 3.25, 0, mat(0xf4f1ea), false);             // ceiling
box(12, 3.2, 0.3, 0, 1.6, -6, wallM);
box(12, 3.2, 0.3, 0, 1.6, 6, wallM);
box(0.3, 3.2, 12, -6, 1.6, 0, wallM);
box(0.3, 3.2, 12, 6, 1.6, 0, wallM);
box(2.4, 0.8, 1.0, -3, 0.4, -5, mat(0x3f6fb0));                 // sofa
box(1.2, 0.75, 1.2, 1, 0.375, -1, mat(0x7a5230, 0.5));          // table
box(1.0, 2.0, 0.5, 5.4, 1, -3, mat(0x5b4030));                  // bookshelf
box(0.8, 0.8, 0.8, -4, 0.4, 3, mat(0xd2873a));                  // crate
box(0.8, 0.8, 0.8, -4, 1.2, 3, mat(0xc9783a));
const lamp = new THREE.PointLight(0xffd9a0, 30, 14, 2);        // physical units: tens of candela, decays with distance
lamp.position.set(0, 2.3, 0);
lamp.castShadow = true;
scene.add(lamp);
scene.add(new THREE.HemisphereLight(0xffffff, 0x554433, 0.8));
const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffe9b0 }));
bulb.position.copy(lamp.position);
scene.add(bulb);

// ---- movement + collision (circle of radius 0.35 against the AABBs, axis by axis so you slide along walls) ----
const keys = new Set();
window.addEventListener('keydown', (e) => keys.add(e.code));
window.addEventListener('keyup', (e) => keys.delete(e.code));
window.addEventListener('blur', () => keys.clear());
const R = 0.35;
function blocked(x, z) {
  return solids.some((s) => x > s.minX - R && x < s.maxX + R && z > s.minZ - R && z < s.maxZ + R);
}
const vel = new THREE.Vector2();
const fwd = new THREE.Vector3(), right = new THREE.Vector3();
function move(dt) {
  const f = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
  const s = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) - (keys.has('KeyA') || keys.has('ArrowLeft') ? 1 : 0);
  const speed = keys.has('ShiftLeft') ? 5 : 3;
  camera.getWorldDirection(fwd);
  fwd.y = 0; fwd.normalize();
  right.crossVectors(fwd, camera.up);
  const k = 1 - Math.exp(-12 * dt);                             // smooth start/stop
  vel.x += ((fwd.x * f + right.x * s) * speed - vel.x) * k;
  vel.y += ((fwd.z * f + right.z * s) * speed - vel.y) * k;
  const p = camera.position;
  if (!blocked(p.x + vel.x * dt, p.z)) p.x += vel.x * dt;       // test X and Z separately
  if (!blocked(p.x, p.z + vel.y * dt)) p.z += vel.y * dt;
  p.y = 1.7 + Math.sin(performance.now() * 0.008) * 0.025 * Math.min(vel.length() / 3, 1);   // head bob
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  move(dt);          // (when PointerLock is unavailable the keys still move you; drag-to-look needs OrbitControls instead)
  renderer.render(scene, camera);
}
animate();
window.__t = { camera, keys, controls, solids };
</script>
</body>
</html>
```
