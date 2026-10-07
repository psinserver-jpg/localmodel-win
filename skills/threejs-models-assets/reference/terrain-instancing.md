---
name: terrain-instancing
description: Procedural terrain from a hand-written value noise with vertex colours by height, transparent water, a 500-tree InstancedMesh forest placed with the height function, and merged rock geometry. Verified in a browser (5 draw calls).
triggers: [terrain, 지형, noise, 노이즈, heightmap, 높이, water, 물, 호수, island, 섬, forest, 숲, instancedmesh, 인스턴스, mergegeometries, buffergeometryutils, 병합, vertex colors, 정점 색, computevertexnormals, mountain, 산, 월드, world]
---
# Terrain + water + instanced forest (verified: 500 trees, 5 draw calls, island with sand/grass/rock/snow)

Tune `heightAt` (frequency `0.03`, amplitude `22`), `WATER` level and colour bands. Drive a character over it by sampling `heightAt(x, z)` for the ground Y. For a flat world drop the noise and keep the instancing.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>절차적 지형</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#bfe3ff}canvas{display:block}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #0007;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">절차적 지형 · 호수 · 인스턴스 숲 (드래그로 회전)</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import * as BufferGeometryUtils from 'three/addons/utils/BufferGeometryUtils.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xbfe3ff);
scene.fog = new THREE.Fog(0xbfe3ff, 60, 170);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 400);
camera.position.set(45, 32, 55);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 3, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 1.1));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.4);
sun.position.set(40, 60, 25);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -60, right: 60, top: 60, bottom: -60, near: 1, far: 160 });
sun.shadow.bias = -0.0005;
sun.shadow.normalBias = 0.05;
scene.add(sun);

// ---- hand-written value noise (no library): smooth random from a seeded hash ----
function hash(ix, iz) { const s = Math.sin(ix * 127.1 + iz * 311.7) * 43758.5453; return s - Math.floor(s); }
function noise(x, z) {
  const ix = Math.floor(x), iz = Math.floor(z), fx = x - ix, fz = z - iz;
  const u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
  const a = hash(ix, iz), b = hash(ix + 1, iz), c = hash(ix, iz + 1), d = hash(ix + 1, iz + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, z) { let h = 0, amp = 1, f = 1, sum = 0; for (let o = 0; o < 4; o++) { h += noise(x * f, z * f) * amp; sum += amp; amp *= 0.5; f *= 2; } return h / sum; }
const SIZE = 120, SEG = 128, WATER = 1.2;
function heightAt(x, z) {
  const d = Math.min(1, Math.hypot(x, z) / (SIZE * 0.5));     // island falloff: lower at the edges
  return (fbm(x * 0.03 + 5, z * 0.03 + 9) * 22 - 6) * (1 - d * d * 0.6) - d * d * 4;
}

// ---- terrain: displace a plane, colour by height, then recompute normals ----
const geo = new THREE.PlaneGeometry(SIZE, SIZE, SEG, SEG);
geo.rotateX(-Math.PI / 2);                                      // lay flat BEFORE reading positions
const pos = geo.attributes.position;
const colors = new Float32Array(pos.count * 3);
const c = new THREE.Color();
for (let i = 0; i < pos.count; i++) {
  const h = heightAt(pos.getX(i), pos.getZ(i));
  pos.setY(i, h);
  if (h < WATER + 0.4) c.set(0xe2cf92);                         // sand
  else if (h < 6) c.set(0x5fae5a).lerp(new THREE.Color(0x3f8f4a), Math.random() * 0.3);
  else if (h < 9) c.set(0x8a8d93);                              // rock
  else c.set(0xf4f6fa);                                         // snow
  colors.set([c.r, c.g, c.b], i * 3);
}
geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
geo.computeVertexNormals();                                     // without this the terrain is flat-lit
const terrain = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, flatShading: true }));
terrain.receiveShadow = true;
terrain.castShadow = true;
scene.add(terrain);

// ---- water: a transparent plane at sea level ----
const water = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ color: 0x2f8fd8, transparent: true, opacity: 0.75, roughness: 0.15, metalness: 0.1 }));
water.rotation.x = -Math.PI / 2;
water.position.y = WATER;
scene.add(water);

// ---- forest: 2 InstancedMeshes (trunks + crowns), placed on the terrain with heightAt ----
const N = 500;
const trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.12, 0.18, 1, 5), new THREE.MeshStandardMaterial({ color: 0x5a3d28 }), N);
const crowns = new THREE.InstancedMesh(new THREE.ConeGeometry(0.9, 2.4, 6), new THREE.MeshStandardMaterial({ color: 0x2c7a3f, flatShading: true }), N);
const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), p = new THREE.Vector3();
let placed = 0, tries = 0;
while (placed < N && tries++ < 20000) {
  const x = (Math.random() - 0.5) * SIZE * 0.9, z = (Math.random() - 0.5) * SIZE * 0.9, h = heightAt(x, z);
  if (h < WATER + 0.8 || h > 6) continue;                      // only on grass
  const k = 0.7 + Math.random() * 0.9;
  q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.random() * 6.28);
  m4.compose(p.set(x, h + 0.5 * k, z), q, sc.set(k, k, k));
  trunks.setMatrixAt(placed, m4);
  m4.compose(p.set(x, h + 1.6 * k, z), q, sc.set(k, k, k));
  crowns.setMatrixAt(placed, m4);
  placed++;
}
trunks.count = crowns.count = placed;                           // draw only what was placed
trunks.castShadow = crowns.castShadow = true;
scene.add(trunks, crowns);

// ---- rocks merged into ONE geometry = one draw call, for static decoration ----
const rockGeos = [];
for (let i = 0; i < 40; i++) {
  const x = (Math.random() - 0.5) * SIZE * 0.8, z = (Math.random() - 0.5) * SIZE * 0.8, h = heightAt(x, z);
  if (h < WATER + 0.5) continue;
  const g = new THREE.DodecahedronGeometry(0.5 + Math.random() * 0.8, 0);
  g.translate(x, h + 0.2, z);
  rockGeos.push(g);
}
const rocks = new THREE.Mesh(BufferGeometryUtils.mergeGeometries(rockGeos), new THREE.MeshStandardMaterial({ color: 0x80848c, flatShading: true }));
rocks.castShadow = true;
scene.add(rocks);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  water.position.y = WATER + Math.sin(clock.elapsedTime * 0.8) * 0.06;   // gentle tide
  controls.update();
  renderer.render(scene, camera);
}
animate();
window.__t = { placed, rocks: rockGeos.length, renderer, heightAt };
</script>
</body>
</html>
```
