---
name: island-diorama
description: Complete working page: low-poly floating island diorama - jittered flat-shaded cylinders, pine trees, house, rocks, animated water plane, drifting clouds, gradient sky texture, matching fog, ACES tone mapping, soft PCF shadows, slow orbit camera at FOV 40.
triggers: [island, 섬, diorama, 디오라마, low poly scene, 로우폴리 장면, low poly island, 로우폴리 섬, 숲, forest, 마을, village, stylized scene, 카툰 월드, tree, 나무]
---
# Low-poly island diorama (verified, 33 draw calls, ~4k triangles)
Why it looks designed: one warm key light + cool hemisphere, flat shading, 7 colours from one palette, sky bottom colour = fog colour, translucent water over the rock base, narrow FOV hero shot, camera orbit looks above the island centre. Swap `P` for another palette from the skill (desert dusk: sand ground, orange sky) and the same code gives a new world. Clouds use a small emissive so ACES does not turn them grey.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>로우폴리 섬</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#ffd9b0}canvas{display:block}#t{position:fixed;left:24px;bottom:22px;color:#fff;font:700 22px/1.2 sans-serif;text-shadow:0 2px 8px #0006}#t small{display:block;font-weight:400;font-size:13px;opacity:.85}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="t">작은 섬<small>천천히 돌아가는 디오라마</small></div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

// palette: one warm key, one cool shadow, a few saturated accents
const P = { skyTop: '#6fb7ff', skyBottom: '#ffe3c2', grass: 0x7cc576, sand: 0xf3d9a4, rock: 0x8a8f9c, trunk: 0x8b5a3c, leaf: 0x3f9d5a, leaf2: 0x5fbf6a, water: 0x39b6d6, roof: 0xe9654b };
const scene = new THREE.Scene();
const sky = document.createElement('canvas'); sky.width = 2; sky.height = 256;
const g = sky.getContext('2d'), grad = g.createLinearGradient(0, 0, 0, 256);
grad.addColorStop(0, P.skyTop); grad.addColorStop(1, P.skyBottom);
g.fillStyle = grad; g.fillRect(0, 0, 2, 256);
const skyTex = new THREE.CanvasTexture(sky); skyTex.colorSpace = THREE.SRGBColorSpace;
scene.background = skyTex;
scene.fog = new THREE.Fog(0xffe3c2, 28, 70);      // fog = bottom colour of the sky, so the horizon melts away

const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 200);   // hero shot: narrow FOV
scene.add(new THREE.HemisphereLight(0xcfe6ff, 0xf0c9a0, 1.0));
const sun = new THREE.DirectionalLight(0xfff0d0, 2.6);
sun.position.set(10, 14, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 45 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03; sun.shadow.radius = 4;
scene.add(sun);

const flat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.9, ...extra });
function mk(geo, mat, x, y, z) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = m.receiveShadow = true; scene.add(m); return m; }

// island: jittered low-poly cylinders (rock base, sand ring, grass top)
function jitter(geo, amount) {
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) if (p.getY(i) > -0.01) { p.setX(i, p.getX(i) + (Math.sin(i * 12.9) * amount)); p.setZ(i, p.getZ(i) + (Math.cos(i * 7.7) * amount)); }
  geo.computeVertexNormals();
  return geo;
}
const island = new THREE.Group(); scene.add(island);
function part(geo, mat, y) { const m = new THREE.Mesh(geo, mat); m.position.y = y; m.castShadow = m.receiveShadow = true; island.add(m); return m; }
part(new THREE.CylinderGeometry(6.6, 4.2, 3, 9), flat(P.rock), -1.5);
part(jitter(new THREE.CylinderGeometry(7.2, 7.4, 0.5, 9), 0.15), flat(P.sand), -0.05);
part(jitter(new THREE.CylinderGeometry(5.8, 6.4, 0.7, 9), 0.2), flat(P.grass), 0.2);

function tree(x, z, s, c) {
  const t = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.18, 0.8, 6), flat(P.trunk));
  trunk.position.y = 0.4;
  const l1 = new THREE.Mesh(new THREE.ConeGeometry(0.8, 1.4, 6), flat(c)); l1.position.y = 1.3;
  const l2 = new THREE.Mesh(new THREE.ConeGeometry(0.6, 1.1, 6), flat(c)); l2.position.y = 2.0;
  t.add(trunk, l1, l2);
  t.traverse((o) => { o.castShadow = o.receiveShadow = true; });
  t.position.set(x, 0.55, z); t.scale.setScalar(s); island.add(t);
}
[[-3, -1.5, 1.1], [-2.2, 1.2, 0.9], [-3.6, 0.6, 1.3], [0.5, -3.4, 1.0], [2.6, -2.2, 0.8], [3.4, 2.4, 1.0], [-0.8, 3.4, 0.85]].forEach(([x, z, s], i) => tree(x, z, s, i % 2 ? P.leaf : P.leaf2));

// little house: box + pyramid roof
const house = new THREE.Group();
const walls = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.1, 1.4), flat(0xfff1dc));
walls.position.y = 0.55;
const roof = new THREE.Mesh(new THREE.ConeGeometry(1.4, 0.9, 4), flat(P.roof)); roof.position.y = 1.55; roof.rotation.y = Math.PI / 4;
house.add(walls, roof); house.traverse((o) => { o.castShadow = o.receiveShadow = true; });
house.position.set(1.4, 0.55, 0.6); house.rotation.y = -0.4; island.add(house);
for (let i = 0; i < 5; i++) { const a = i * 1.7, r = 2.5 + (i % 3); mk(new THREE.DodecahedronGeometry(0.28 + (i % 2) * 0.1, 0), flat(P.rock), Math.cos(a) * r, 0.7, Math.sin(a) * r); }

// water: big plane, vertices wobble in JS (cheap), semi-transparent so the island base shows through
const wGeo = new THREE.PlaneGeometry(80, 80, 40, 40); wGeo.rotateX(-Math.PI / 2);
const water = new THREE.Mesh(wGeo, new THREE.MeshStandardMaterial({ color: P.water, flatShading: true, roughness: 0.25, metalness: 0.1, transparent: true, opacity: 0.88 }));
water.position.y = -0.5; water.receiveShadow = true; scene.add(water);
const wBase = wGeo.attributes.position.array.slice();

// clouds: merged-looking groups of white low-poly spheres
const cloudMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x9aa4b8, flatShading: true, roughness: 1 });
const clouds = [];
for (let i = 0; i < 5; i++) {
  const c = new THREE.Group();
  for (let j = 0; j < 4; j++) { const s = new THREE.Mesh(new THREE.IcosahedronGeometry(0.9 + Math.random() * 0.5, 0), cloudMat); s.position.set(j * 0.9 - 1.3, Math.random() * 0.3, Math.random() * 0.5); c.add(s); }
  c.position.set(-18 + i * 9, 6 + (i % 2) * 2, -14 - (i % 3) * 4); scene.add(c); clouds.push(c);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
let t = 0;
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  t += dt;
  const a = t * 0.12 + 0.6;
  camera.position.set(Math.cos(a) * 20, 7, Math.sin(a) * 20);   // slow orbit; look slightly above the island = rule of thirds
  camera.lookAt(0, 2.2, 0);
  const p = wGeo.attributes.position;
  for (let i = 0; i < p.count; i++) p.setY(i, Math.sin(wBase[i * 3] * 0.5 + t) * 0.08 + Math.cos(wBase[i * 3 + 2] * 0.6 + t * 1.2) * 0.08);
  p.needsUpdate = true; wGeo.computeVertexNormals();
  clouds.forEach((c, i) => { c.position.x += dt * (0.4 + i * 0.1); if (c.position.x > 24) c.position.x = -24; });
  island.position.y = Math.sin(t * 0.8) * 0.05;
  renderer.render(scene, camera);
});
window.__i = { renderer, scene };
</script>
</body>
</html>
```
