---
name: recipes
description: Copy-paste three.js lighting moods (daylight, golden hour, night, studio) and materials (toon, glass, neon, metal, procedural checker and noise textures, gradient sky) with a runnable showcase page.
triggers: [golden hour, sunset, 노을, night, 밤, studio lighting, 스튜디오, product shot, toon material, gradientmap, 툰 셰이딩, glass material, 유리 재질, neon, 네온, procedural texture, canvastexture, checker, 체커, gradient sky, 하늘, daylight, 낮, moon, 달빛]
---
# Lighting moods and material recipes

## Moods (swap into the lighting block)
```js
// fragment
function mood(name) {
  const m = {
    day:     { bg: 0xbfe3ff, fog: [25, 90], hemi: [0xcfe8ff, 0x7a6a4f, 1.0], sun: [0xfff1d6, 2.4, [8, 14, 6]] },
    golden:  { bg: 0xffc58a, fog: [15, 70], hemi: [0xffd2a1, 0x5a4636, 0.7], sun: [0xff9a4d, 3.0, [-12, 4, 6]] },
    night:   { bg: 0x0a1230, fog: [10, 55], hemi: [0x274a8a, 0x0a0f20, 0.5], sun: [0x8fb4ff, 0.9, [6, 12, -4]] },
    overcast:{ bg: 0xaab4bd, fog: [10, 60], hemi: [0xdfe6ec, 0x6b6f73, 1.3], sun: [0xffffff, 0.8, [3, 10, 3]] },
  }[name];
  scene.background = new THREE.Color(m.bg);
  scene.fog = new THREE.Fog(m.bg, m.fog[0], m.fog[1]);
  hemi.color.set(m.hemi[0]); hemi.groundColor.set(m.hemi[1]); hemi.intensity = m.hemi[2];
  sun.color.set(m.sun[0]); sun.intensity = m.sun[1]; sun.position.set(...m.sun[2]);
}
```
(`hemi` and `sun` are the lights you created.) Night scenes: add 2-3 `PointLight(0xffb066, 80, 20)` lamps and emissive windows.

## Studio / product shot (3-point)
```js
// fragment
const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(4, 5, 5);
const fill = new THREE.DirectionalLight(0x9ec9ff, 0.8); fill.position.set(-5, 2, 3);
const rim = new THREE.DirectionalLight(0xffffff, 2.0); rim.position.set(0, 4, -6);
scene.add(key, fill, rim);
scene.background = new THREE.Color(0x15171c);
```
Add `RoomEnvironment` (see SKILL.md) for reflections and `OrbitControls` with `autoRotate = true`.

## Toon material (3-step shading)
```js
// fragment
const steps = new Uint8Array([90, 170, 255]);
const gradientMap = new THREE.DataTexture(steps, steps.length, 1, THREE.RedFormat);
gradientMap.minFilter = gradientMap.magFilter = THREE.NearestFilter;   // hard bands
gradientMap.needsUpdate = true;
const toon = new THREE.MeshToonMaterial({ color: 0xff8a65, gradientMap });
```

## Glass, metal, neon
```js
// fragment
const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, transmission: 1, thickness: 0.6, roughness: 0.05, ior: 1.45, transparent: true });
const gold = new THREE.MeshStandardMaterial({ color: 0xffc94d, metalness: 1, roughness: 0.25 });   // needs scene.environment
const neon = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: 0x00e5ff, emissiveIntensity: 2.5 });
```
Transmission renders the scene behind it again: use on 1-3 objects only.

## Procedural textures (no image files)
```js
// fragment
function checkerTexture(a = '#e9e4d8', b = '#b9b09a', size = 512, cells = 8) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d'), s = size / cells;
  for (let y = 0; y < cells; y++) for (let x = 0; x < cells; x++) { g.fillStyle = (x + y) % 2 ? a : b; g.fillRect(x * s, y * s, s, s); }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}
function noiseTexture(size = 256, base = 128, spread = 40) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d'), img = g.createImageData(size, size);
  for (let i = 0; i < img.data.length; i += 4) { const v = base + (Math.random() - 0.5) * spread; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
// floor: floorMat.map = checkerTexture(); floorMat.map.repeat.set(10, 10);   bumpMap = noiseTexture(), bumpScale = 0.4
```

## Gradient sky (no skybox file)
```js
// fragment
function skyTexture(top = '#3d7bd9', bottom = '#e8f4ff') {
  const c = document.createElement('canvas'); c.width = 4; c.height = 256;
  const g = c.getContext('2d'), grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, top); grad.addColorStop(1, bottom);
  g.fillStyle = grad; g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
// scene.background = skyTexture();   (fog colour = the bottom colour)
```

## Showcase page (every material above, lit and shadowed)
```html
<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>재질 쇼케이스</title>
<style>html,body{margin:0;height:100%;overflow:hidden}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script></head>
<body><script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xbfe3ff);
scene.fog = new THREE.Fog(0xbfe3ff, 25, 90);
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 4, 11);
const hemi = new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 0.8);
const sun = new THREE.DirectionalLight(0xfff1d6, 2.4);
sun.position.set(8, 14, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 50 });
sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.02;
scene.add(hemi, sun);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({ color: 0xe9e4d8, roughness: 0.9 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const steps = new Uint8Array([90, 170, 255]);
const gradientMap = new THREE.DataTexture(steps, 3, 1, THREE.RedFormat);
gradientMap.minFilter = gradientMap.magFilter = THREE.NearestFilter; gradientMap.needsUpdate = true;
const mats = [
  new THREE.MeshStandardMaterial({ color: 0xff7043, roughness: 0.6 }),
  new THREE.MeshStandardMaterial({ color: 0xffc94d, metalness: 1, roughness: 0.25 }),
  new THREE.MeshPhysicalMaterial({ color: 0xffffff, transmission: 1, thickness: 0.6, roughness: 0.05, ior: 1.45 }),
  new THREE.MeshToonMaterial({ color: 0x7e57c2, gradientMap }),
  new THREE.MeshStandardMaterial({ color: 0x111111, emissive: 0x00e5ff, emissiveIntensity: 2.5 }),
  new THREE.MeshStandardMaterial({ color: 0x66bb6a, flatShading: true, roughness: 0.8 }),
];
const spheres = mats.map((m, i) => {
  const s = new THREE.Mesh(i === 5 ? new THREE.IcosahedronGeometry(1, 1) : new THREE.SphereGeometry(1, 48, 32), m);
  s.position.set((i - 2.5) * 2.4, 1, 0); s.castShadow = true; scene.add(s); return s;
});
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1, 0); controls.enableDamping = true;
window.addEventListener('resize', () => { camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); });
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  spheres.forEach((s, i) => { s.position.y = 1 + Math.abs(Math.sin(t * 1.5 + i * 0.6)) * 0.5; s.rotation.y = t * 0.5; });
  controls.update(); renderer.render(scene, camera);
}
animate();
</script></body></html>
```
