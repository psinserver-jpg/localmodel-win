---
name: snow-fireflies
description: Night snow scene with 3000 falling snow points, pulsing fireflies, a star dome and an InstancedMesh pine forest, all dt-based. Verified in a browser.
triggers: [snow, 눈, 눈 내리는, rain, 비, fireflies, 반딧불, stars, 별, 별하늘, instancedmesh, 인스턴스, forest, 숲, night, 밤, ambient particles, wrap]
---
# Snow + fireflies + stars + instanced forest (verified: snow y decreases, fireflies glow, no errors)

Rain variant: same loop, speed 15-25, `size 0.05`, `color 0xaaccff`, slight x drift, `opacity 0.6`. Snow uses normal blending (fades by opacity, white on dark); fireflies use additive blending (glow). Animating an InstancedMesh: reuse one `Matrix4`, call `setMatrixAt(i, m)` for each moving item, then `mesh.instanceMatrix.needsUpdate = true`; set `mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)` first.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>눈 내리는 밤</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#0a1020}canvas{display:block}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #000a;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">눈 내리는 밤 · 반딧불이 · 드래그로 회전</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a1020);
scene.fog = new THREE.FogExp2(0x0a1020, 0.03);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 150);
camera.position.set(0, 3, 10);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.5, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;

scene.add(new THREE.HemisphereLight(0x8fa8ff, 0x1a2030, 0.9));
const moon = new THREE.DirectionalLight(0xbcd0ff, 1.6);
moon.position.set(-6, 10, 4);
moon.castShadow = true;
Object.assign(moon.shadow.camera, { left: -14, right: 14, top: 14, bottom: -14, near: 1, far: 40 });
scene.add(moon);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ color: 0xdfe8f5, roughness: 0.95 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

function softDot() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.5, 'rgba(255,255,255,0.35)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}
const dot = softDot();

// pine trees: InstancedMesh = 1 draw call for 60 cones
const cone = new THREE.InstancedMesh(new THREE.ConeGeometry(1, 3, 7), new THREE.MeshStandardMaterial({ color: 0x1f4d3a, flatShading: true }), 60);
const trunk = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.15, 0.2, 1, 6), new THREE.MeshStandardMaterial({ color: 0x4a3426 }), 60);
const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
for (let i = 0; i < 60; i++) {
  let a, r;
  do { a = Math.random() * Math.PI * 2; r = 4 + Math.random() * 26; } while (Math.hypot(Math.cos(a) * r, Math.sin(a) * r - 10) < 5);   // keep the camera spot clear
  const k = 0.5 + Math.random() * 0.8;
  p.set(Math.cos(a) * r, 1.5 * k + 0.5, Math.sin(a) * r);
  m4.compose(p, q, s.set(k, k, k)); cone.setMatrixAt(i, m4);
  p.y = 0.5 * k;
  m4.compose(p, q, s.set(k, k, k)); trunk.setMatrixAt(i, m4);
}
cone.castShadow = true;
scene.add(cone, trunk);

// snow: positions only, wrapped inside a box around the origin
const SNOW = 3000, BOX = { x: 40, y: 18, z: 40 };
const snowPos = new Float32Array(SNOW * 3), snowSeed = new Float32Array(SNOW);
for (let i = 0; i < SNOW; i++) {
  snowPos[i * 3] = (Math.random() - 0.5) * BOX.x;
  snowPos[i * 3 + 1] = Math.random() * BOX.y;
  snowPos[i * 3 + 2] = (Math.random() - 0.5) * BOX.z;
  snowSeed[i] = Math.random() * 100;
}
const snowGeo = new THREE.BufferGeometry();
snowGeo.setAttribute('position', new THREE.BufferAttribute(snowPos, 3));
const snow = new THREE.Points(snowGeo, new THREE.PointsMaterial({ size: 0.18, map: dot, color: 0xffffff, transparent: true, depthWrite: false, sizeAttenuation: true }));
snow.frustumCulled = false;
scene.add(snow);

// fireflies: additive glow, each drifts on its own sine paths
const FLY = 40;
const flyPos = new Float32Array(FLY * 3), flyBase = [], flySeed = [];
for (let i = 0; i < FLY; i++) {
  flyBase.push(new THREE.Vector3((Math.random() - 0.5) * 16, 0.8 + Math.random() * 2.5, (Math.random() - 0.5) * 16));
  flySeed.push(Math.random() * 100);
}
const flyGeo = new THREE.BufferGeometry();
flyGeo.setAttribute('position', new THREE.BufferAttribute(flyPos, 3));
const flyMat = new THREE.PointsMaterial({ size: 0.7, map: dot, color: 0xfff08a, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
const flies = new THREE.Points(flyGeo, flyMat);
flies.frustumCulled = false;
scene.add(flies);

// stars: static, far away, never updated
const starPos = new Float32Array(600 * 3);
for (let i = 0; i < 600; i++) {
  const v = new THREE.Vector3().randomDirection().multiplyScalar(90);
  v.y = Math.abs(v.y);
  starPos.set([v.x, v.y, v.z], i * 3);
}
const starGeo = new THREE.BufferGeometry();
starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ size: 1.2, color: 0xffffff, fog: false, sizeAttenuation: false })));

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
  for (let i = 0; i < SNOW; i++) {
    const k = i * 3;
    snowPos[k + 1] -= (1.0 + (snowSeed[i] % 1)) * dt;                // fall speed 1-2 m/s
    snowPos[k] += Math.sin(t * 0.8 + snowSeed[i]) * 0.4 * dt;         // sway
    if (snowPos[k + 1] < 0) snowPos[k + 1] += BOX.y;                  // wrap to the top, no allocation
  }
  snowGeo.attributes.position.needsUpdate = true;
  for (let i = 0; i < FLY; i++) {
    const b = flyBase[i], sd = flySeed[i];
    flyPos[i * 3] = b.x + Math.sin(t * 0.5 + sd) * 1.5;
    flyPos[i * 3 + 1] = b.y + Math.sin(t * 0.9 + sd * 2) * 0.5;
    flyPos[i * 3 + 2] = b.z + Math.cos(t * 0.4 + sd) * 1.5;
  }
  flyGeo.attributes.position.needsUpdate = true;
  flyMat.opacity = 0.7 + Math.sin(t * 3) * 0.3;                       // pulsing glow (shared by all)
  controls.update();
  renderer.render(scene, camera);
}
animate();
window.__t = { snowPos, flyPos, get t() { return t; } };
</script>
</body>
</html>
```
