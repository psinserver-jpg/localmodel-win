---
name: primitives-village
description: Factory functions that build a tree, house, car, robot with pivot limbs, cactus, rock and mountain from primitives, composed into a lit village with sky, fog and shadows. Verified in a browser.
triggers: [primitives, 프리미티브, factory, 팩토리, tree, 나무, house, 집, car, 자동차, robot, 로봇, cactus, 선인장, rock, 바위, mountain, 산, village, 마을, low poly, 로우폴리, pivot, group, 캐릭터, character]
---
# Primitive models + village (verified: car drives, robot limbs swing, shadows/fog render, no errors)

Copy the factories into any scene. Each returns a `Group` standing on y = 0. Robot limbs are pivots in `userData.limbs`. Change colours in `M`, sizes via parameters. For a character: reuse `makeRobot` proportions, swap box head for a sphere, add hair/hat as extra parts.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>작은 마을</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#9fd3ff}canvas{display:block}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #0007;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">작은 마을 · 드래그로 회전, 휠로 확대</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fd3ff);
scene.fog = new THREE.Fog(0x9fd3ff, 40, 110);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 300);
camera.position.set(16, 12, 20);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.48;

scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 1.0));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.4);
sun.position.set(14, 22, 10);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30, near: 1, far: 80 });
sun.shadow.bias = -0.0005;
sun.shadow.normalBias = 0.02;
scene.add(sun);

// ---- helpers: shared materials, one call makes a shadow-casting mesh ----
const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.9, ...extra });
const M = { wood: mat(0x6b4a2f), leaf: mat(0x2f8f4e), leaf2: mat(0x3fae5f), wall: mat(0xf1e4cf), roof: mat(0xc2452d), glass: mat(0x9fd6ff, { roughness: 0.2 }),
  stone: mat(0x8a8d93), sand: mat(0xe0c27a), cactus: mat(0x4a9a56), body: mat(0x2f6fd0), dark: mat(0x222831), skin: mat(0xf2c29b), metal: mat(0xb7bec9, { metalness: 0.6, roughness: 0.4 }) };
function part(geo, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

// ---- factories: each returns a Group whose origin is at the feet (y = 0 is the ground) ----
function makeTree(scale = 1) {
  const g = new THREE.Group();
  g.add(part(new THREE.CylinderGeometry(0.15, 0.22, 1, 6), M.wood, 0, 0.5, 0));
  g.add(part(new THREE.ConeGeometry(1.0, 1.8, 7), M.leaf, 0, 1.7, 0));
  g.add(part(new THREE.ConeGeometry(0.75, 1.4, 7), M.leaf2, 0, 2.5, 0));
  g.scale.setScalar(scale);
  return g;
}
function makeHouse(w = 3, d = 3, h = 2) {
  const g = new THREE.Group();
  g.add(part(new THREE.BoxGeometry(w, h, d), M.wall, 0, h / 2, 0));
  const roof = part(new THREE.ConeGeometry(Math.max(w, d) * 0.78, 1.4, 4), M.roof, 0, h + 0.7, 0);
  roof.rotation.y = Math.PI / 4;
  g.add(roof);
  g.add(part(new THREE.BoxGeometry(0.6, 1.1, 0.08), M.wood, 0, 0.55, d / 2 + 0.02));       // door
  g.add(part(new THREE.BoxGeometry(0.6, 0.6, 0.08), M.glass, w / 2 - 0.7, h * 0.6, d / 2 + 0.02)); // window
  g.add(part(new THREE.BoxGeometry(0.4, 0.9, 0.4), M.stone, -w / 4, h + 1.0, 0));            // chimney
  return g;
}
function makeCar(color = 0xd23b3b) {
  const g = new THREE.Group();
  g.add(part(new THREE.BoxGeometry(2.2, 0.5, 1.0), mat(color), 0, 0.45, 0));
  g.add(part(new THREE.BoxGeometry(1.1, 0.45, 0.9), M.glass, -0.1, 0.9, 0));
  for (const [x, z] of [[-0.7, 0.5], [0.7, 0.5], [-0.7, -0.5], [0.7, -0.5]]) {
    const wheel = part(new THREE.CylinderGeometry(0.25, 0.25, 0.2, 12), M.dark, x, 0.25, z);
    wheel.rotation.x = Math.PI / 2;
    g.add(wheel);
  }
  return g;
}
function makeRobot() {            // pivots at shoulders/hips so limbs rotate around the joint
  const g = new THREE.Group();
  g.add(part(new THREE.BoxGeometry(0.8, 1.0, 0.5), M.metal, 0, 1.5, 0));
  g.add(part(new THREE.BoxGeometry(0.55, 0.5, 0.5), M.body, 0, 2.3, 0));
  g.add(part(new THREE.SphereGeometry(0.08, 8, 8), mat(0xffe066, { emissive: 0xffc400 }), -0.14, 2.35, 0.26));
  g.add(part(new THREE.SphereGeometry(0.08, 8, 8), mat(0xffe066, { emissive: 0xffc400 }), 0.14, 2.35, 0.26));
  const limbs = {};
  for (const [name, x, y, len] of [['armL', -0.55, 1.95, 0.9], ['armR', 0.55, 1.95, 0.9], ['legL', -0.22, 1.0, 1.0], ['legR', 0.22, 1.0, 1.0]]) {
    const pivot = new THREE.Group();
    pivot.position.set(x, y, 0);
    pivot.add(part(new THREE.BoxGeometry(0.25, len, 0.25), name.startsWith('arm') ? M.body : M.dark, 0, -len / 2, 0));
    g.add(pivot);
    limbs[name] = pivot;
  }
  g.userData.limbs = limbs;
  return g;
}
function makeCactus() {
  const g = new THREE.Group();
  g.add(part(new THREE.CylinderGeometry(0.25, 0.3, 1.8, 8), M.cactus, 0, 0.9, 0));
  const armH = part(new THREE.CylinderGeometry(0.14, 0.14, 0.5, 8), M.cactus, 0.4, 1.0, 0);
  armH.rotation.z = Math.PI / 2;                                  // sideways stub
  g.add(armH, part(new THREE.CylinderGeometry(0.14, 0.14, 0.6, 8), M.cactus, 0.65, 1.3, 0));
  return g;
}
function makeRock(size = 1) {
  const m = part(new THREE.DodecahedronGeometry(size * 0.6, 0), M.stone, 0, size * 0.4, 0);
  m.scale.set(1, 0.7, 0.9);
  m.rotation.set(Math.random(), Math.random() * 6, 0);
  const g = new THREE.Group();
  g.add(m);
  return g;
}
function makeMountain(h = 12, r = 9) {
  const g = new THREE.Group();
  g.add(part(new THREE.ConeGeometry(r, h, 6), M.stone, 0, h / 2, 0));
  g.add(part(new THREE.ConeGeometry(r * 0.36, h * 0.3, 6), mat(0xffffff), 0, h * 0.85, 0));
  return g;
}

// ---- compose the village ----
const ground = new THREE.Mesh(new THREE.CircleGeometry(60, 48), mat(0x7bc96f));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
const road = new THREE.Mesh(new THREE.PlaneGeometry(40, 3), mat(0x555a63));
road.rotation.x = -Math.PI / 2;
road.position.y = 0.02;
road.receiveShadow = true;
scene.add(road);

[[-9, -6, 0.1], [-3, -7, -0.2], [4, -6.5, 0.15], [10, -6, 0]].forEach(([x, z, r], i) => {
  const h = makeHouse(3 + (i % 2), 3, 2 + (i % 3) * 0.4);
  h.position.set(x, 0, z);
  h.rotation.y = r;
  scene.add(h);
});
const house2 = makeHouse(3.5, 3, 2.4);
house2.position.set(-6, 0, 7);
house2.rotation.y = Math.PI;
scene.add(house2);

for (let i = 0; i < 28; i++) {
  const a = Math.random() * Math.PI * 2, r = 14 + Math.random() * 22;
  const t = makeTree(0.8 + Math.random() * 0.8);
  t.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
  scene.add(t);
}
for (let i = 0; i < 8; i++) {
  const rk = makeRock(0.6 + Math.random());
  rk.position.set((Math.random() - 0.5) * 40, 0, 10 + Math.random() * 12);
  scene.add(rk);
}
const cactus = makeCactus();
cactus.position.set(12, 0, 8);
scene.add(cactus);
const mount = [[-30, -38, 14, 11], [10, -45, 18, 14], [38, -32, 12, 9]];
mount.forEach(([x, z, h, r]) => { const m = makeMountain(h, r); m.position.set(x, 0, z); scene.add(m); });

const car = makeCar();
car.position.set(-18, 0, 0.6);
scene.add(car);
const robot = makeRobot();
robot.position.set(2, 0, 4);
scene.add(robot);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
let t = 0;
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  t += dt;
  car.position.x += dt * 4;
  if (car.position.x > 20) car.position.x = -20;
  const L = robot.userData.limbs;                               // walk cycle: opposite arm/leg swing
  L.legL.rotation.x = Math.sin(t * 4) * 0.7;
  L.legR.rotation.x = -Math.sin(t * 4) * 0.7;
  L.armL.rotation.x = -Math.sin(t * 4) * 0.6;
  L.armR.rotation.x = Math.sin(t * 4) * 0.6;
  robot.position.y = Math.abs(Math.sin(t * 4)) * 0.05;
  controls.update();
  renderer.render(scene, camera);
}
animate();
window.__t = { car, robot, scene, get t() { return t; } };
</script>
</body>
</html>
```
