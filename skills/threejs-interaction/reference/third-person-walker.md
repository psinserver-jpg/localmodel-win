---
name: third-person-walker
description: Third-person WASD/arrow walker with camera-relative movement, damped speed and turning, leg and arm swing, AABB obstacle sliding, smooth follow camera and a pointer-event virtual joystick for phones. Verified in a browser.
triggers: [walker, 걷기, third person, 3인칭, wasd, 키보드, keyboard, character controller, 캐릭터 조작, joystick, 조이스틱, touch, 터치, mobile, 모바일, follow camera, 따라가는 카메라, collision, 충돌, run, 달리기]
---
# Third-person walker (verified: W moved 3.3 m in 1.5 s, D turned/strafed, joystick drove it, box collision stops at radius 0.4)

The joystick is `display:none` on desktops (`@media (pointer:coarse)` shows it). Replace the primitive character by a `makeRobot()`/GLB model facing +Z (see `threejs-models-assets`); with a GLB switch Idle/Walk clips by `speed`. Add jumping: `vy -= 25*dt`, `Space` sets `vy = 9` when `player.position.y <= 0`.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>3인칭 걷기</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#9fd3ff;touch-action:none;user-select:none}canvas{display:block}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #0007;pointer-events:none}
#joy{position:fixed;left:24px;bottom:24px;width:120px;height:120px;border-radius:50%;background:#ffffff40;display:none;touch-action:none}
#knob{position:absolute;left:40px;top:40px;width:40px;height:40px;border-radius:50%;background:#ffffffcc}
@media (pointer:coarse){#joy{display:block}}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
</head>
<body>
<div id="hud">WASD 또는 방향키로 이동 · Shift 달리기 · 모바일은 왼쪽 조이스틱</div>
<div id="joy"><div id="knob"></div></div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fd3ff);
scene.fog = new THREE.Fog(0x9fd3ff, 25, 70);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 150);

scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 1.1));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.4);
sun.position.set(10, 20, 8);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25, near: 1, far: 60 });
scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshStandardMaterial({ color: 0x7bc96f }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// obstacles: boxes the player cannot walk through (AABB in XZ)
const boxes = [];
for (let i = 0; i < 14; i++) {
  const w = 1.5 + Math.random() * 3, h = 1 + Math.random() * 3, d = 1.5 + Math.random() * 3;
  const x = (Math.random() - 0.5) * 50, z = (Math.random() - 0.5) * 50;
  if (Math.hypot(x, z) < 5) continue;                        // keep the spawn clear
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(Math.random(), 0.5, 0.6), flatShading: true }));
  m.position.set(x, h / 2, z);
  m.castShadow = m.receiveShadow = true;
  scene.add(m);
  boxes.push({ x, z, hw: w / 2, hd: d / 2 });
}

// character: pivots at hips/shoulders
const player = new THREE.Group();
const skin = new THREE.MeshStandardMaterial({ color: 0xf2c29b }), shirt = new THREE.MeshStandardMaterial({ color: 0x3f7be0 }), pants = new THREE.MeshStandardMaterial({ color: 0x2b3245 });
function limb(mat, x, y, len) {
  const pivot = new THREE.Group();
  pivot.position.set(x, y, 0);
  const m = new THREE.Mesh(new THREE.BoxGeometry(0.22, len, 0.22), mat);
  m.position.y = -len / 2;
  m.castShadow = true;
  pivot.add(m);
  player.add(pivot);
  return pivot;
}
const torso = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.7, 0.32), shirt);
torso.position.y = 1.25;
const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 16, 12), skin);
head.position.y = 1.85;
torso.castShadow = head.castShadow = true;
player.add(torso, head);
for (const x of [-0.08, 0.08]) {                              // eyes on +Z so you can see which way it faces
  const eye = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), new THREE.MeshBasicMaterial({ color: 0x111111 }));
  eye.position.set(x, 1.88, 0.2);
  player.add(eye);
}
const legL = limb(pants, -0.15, 0.9, 0.9), legR = limb(pants, 0.15, 0.9, 0.9), armL = limb(shirt, -0.4, 1.55, 0.7), armR = limb(shirt, 0.4, 1.55, 0.7);
scene.add(player);

// ---- input: keyboard + virtual joystick produce one vector (x = right, y = forward) ----
const keys = new Set();
window.addEventListener('keydown', (e) => { keys.add(e.code); if (e.code.startsWith('Arrow') || e.code === 'Space') e.preventDefault(); });
window.addEventListener('keyup', (e) => keys.delete(e.code));
window.addEventListener('blur', () => keys.clear());          // no stuck keys after alt-tab
const joy = { x: 0, y: 0, id: null };
const joyEl = document.getElementById('joy'), knob = document.getElementById('knob');
function joyMove(e) {
  const r = joyEl.getBoundingClientRect();
  let dx = (e.clientX - (r.left + r.width / 2)) / 40, dy = (e.clientY - (r.top + r.height / 2)) / 40;
  const len = Math.hypot(dx, dy);
  if (len > 1) { dx /= len; dy /= len; }
  joy.x = dx; joy.y = -dy;
  knob.style.transform = `translate(${dx * 40}px, ${dy * 40}px)`;
}
joyEl.addEventListener('pointerdown', (e) => {
  joy.id = e.pointerId;
  try { joyEl.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events */ }
  joyMove(e);
});
joyEl.addEventListener('pointermove', (e) => { if (e.pointerId === joy.id) joyMove(e); });
const joyEnd = () => { joy.id = null; joy.x = joy.y = 0; knob.style.transform = ''; };
joyEl.addEventListener('pointerup', joyEnd);
joyEl.addEventListener('pointercancel', joyEnd);
function inputVector() {
  let x = joy.x, y = joy.y;
  if (keys.has('KeyW') || keys.has('ArrowUp')) y += 1;
  if (keys.has('KeyS') || keys.has('ArrowDown')) y -= 1;
  if (keys.has('KeyD') || keys.has('ArrowRight')) x += 1;
  if (keys.has('KeyA') || keys.has('ArrowLeft')) x -= 1;
  const v = new THREE.Vector2(x, y);
  if (v.length() > 1) v.normalize();                          // diagonals are not faster
  return v;
}

function resolveCollisions(p, radius) {
  for (const b of boxes) {                                     // push the circle out of each box
    const cx = THREE.MathUtils.clamp(p.x, b.x - b.hw, b.x + b.hw), cz = THREE.MathUtils.clamp(p.z, b.z - b.hd, b.z + b.hd);
    const dx = p.x - cx, dz = p.z - cz, d = Math.hypot(dx, dz);
    if (d < radius) {
      if (d > 1e-6) { p.x = cx + (dx / d) * radius; p.z = cz + (dz / d) * radius; }
      else p.x = b.x + b.hw + radius;                          // centre inside the box: eject along +x
    }
  }
}
const damp = (a, b, lambda, dt) => THREE.MathUtils.lerp(a, b, 1 - Math.exp(-lambda * dt));
function dampAngle(a, b, lambda, dt) {                         // shortest way around the circle
  let d = ((b - a + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
  return a + d * (1 - Math.exp(-lambda * dt));
}

const camOffset = new THREE.Vector3(0, 4.5, 8);
const camPos = new THREE.Vector3(0, 5, 10), lookAt = new THREE.Vector3();
const fwd = new THREE.Vector3(), right = new THREE.Vector3(), move = new THREE.Vector3();
let heading = 0, walkT = 0, speed = 0;

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  const input = inputVector();
  const run = keys.has('ShiftLeft') || keys.has('ShiftRight');
  // camera-relative directions on the ground
  camera.getWorldDirection(fwd);
  fwd.y = 0; fwd.normalize();
  right.crossVectors(fwd, camera.up).normalize();
  move.set(0, 0, 0).addScaledVector(fwd, input.y).addScaledVector(right, input.x);
  const target = input.length() * (run ? 7 : 4);
  speed = damp(speed, target, 10, dt);                          // accelerate/decelerate smoothly
  if (input.length() > 0.05) {
    heading = dampAngle(heading, Math.atan2(move.x, move.z), 12, dt);   // face where we walk (model front = +Z)
    player.position.addScaledVector(move.normalize(), speed * dt);
    resolveCollisions(player.position, 0.4);
  }
  player.rotation.y = heading;
  walkT += dt * speed * 2.2;                                    // swing speed follows walking speed
  const swing = Math.min(speed / 4, 1.2) * 0.7;
  legL.rotation.x = Math.sin(walkT) * swing; legR.rotation.x = -Math.sin(walkT) * swing;
  armL.rotation.x = -Math.sin(walkT) * swing; armR.rotation.x = Math.sin(walkT) * swing;
  // follow camera: fixed offset behind the player (world axes), smoothed
  const want = player.position.clone().add(camOffset);
  camPos.x = damp(camPos.x, want.x, 4, dt); camPos.y = damp(camPos.y, want.y, 4, dt); camPos.z = damp(camPos.z, want.z, 4, dt);
  camera.position.copy(camPos);
  lookAt.set(player.position.x, player.position.y + 1.2, player.position.z);
  camera.lookAt(lookAt);
  renderer.render(scene, camera);
}
animate();
window.__t = { player, keys, joy, joyEl, get speed() { return speed; }, boxes };
</script>
</body>
</html>
```
