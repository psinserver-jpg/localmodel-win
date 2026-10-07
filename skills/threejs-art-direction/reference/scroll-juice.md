---
name: scroll-juice
description: Complete scroll-driven 3D page (camera along a CatmullRomCurve3, eased progress, text sections toggled by progress, depth-layered debris) plus verified juice helpers - easing, damp, squash and stretch, pop-in, camera shake with trauma, light flicker.
triggers: [scroll driven, 스크롤 연동, scroll camera, 스크롤 카메라, 스크롤 3d, camera path, 카메라 경로, catmullromcurve3, product page, 제품 소개 페이지, squash and stretch, 스쿼시, camera shake, 카메라 흔들림, juice, 타격감, easing, 이징, flicker]
---
# Scroll-driven camera + juice (verified)
Scroll test: progress 0 -> camera (6,2,9); 0.4 -> (1.5,0.5,3.5) and section 2 visible; 1 -> (-8,5,10). Text sections need `z-index` above the fixed canvas.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>스크롤 카메라</title>
<style>
html,body{margin:0;background:#0e1020}
canvas{position:fixed;inset:0;display:block}
#spacer{height:500vh}
section{position:fixed;z-index:2;left:6vw;bottom:10vh;max-width:min(420px,88vw);color:#fff;font:16px/1.6 sans-serif;opacity:0;transition:opacity .5s;pointer-events:none}
section h2{margin:0 0 6px;font-size:clamp(24px,5vw,40px)}
section.on{opacity:1}
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"}}</script>
</head>
<body>
<section id="s0" class="on"><h2>시작</h2>아래로 스크롤하세요.</section>
<section id="s1"><h2>디자인</h2>가까이 다가갑니다.</section>
<section id="s2"><h2>마무리</h2>멀리서 전체를 봅니다.</section>
<div id="spacer"></div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e1020);
scene.fog = new THREE.Fog(0x0e1020, 12, 40);
const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
scene.add(new THREE.HemisphereLight(0xaac4ff, 0x331133, 1.0));
const key = new THREE.DirectionalLight(0xfff1d6, 2.5);
key.position.set(4, 6, 5);
scene.add(key);

const product = new THREE.Mesh(new THREE.TorusKnotGeometry(1, 0.32, 160, 24), new THREE.MeshStandardMaterial({ color: 0xff6b9d, roughness: 0.25, metalness: 0.6 }));
scene.add(product);
for (let i = 0; i < 40; i++) {   // depth layering: small debris around the hero
  const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.1 + Math.random() * 0.25, 0), new THREE.MeshStandardMaterial({ color: 0x6c8cff, flatShading: true }));
  m.position.set((Math.random() - 0.5) * 16, (Math.random() - 0.5) * 8, (Math.random() - 0.5) * 16);
  scene.add(m);
}

// camera path: a smooth curve; scroll progress 0..1 picks a point on it
const path = new THREE.CatmullRomCurve3([new THREE.Vector3(6, 2, 9), new THREE.Vector3(2.5, 0.5, 4), new THREE.Vector3(-3, 1, 3.5), new THREE.Vector3(-8, 5, 10)], false, 'catmullrom', 0.5);
const look = new THREE.Vector3(), target = new THREE.Vector3(0, 0, 0);
let progress = 0, shown = 0;
const sections = [...document.querySelectorAll('section')];
function readScroll() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  progress = max > 0 ? THREE.MathUtils.clamp(window.scrollY / max, 0, 1) : 0;
}
window.addEventListener('scroll', readScroll, { passive: true });
readScroll();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  shown += (progress - shown) * (1 - Math.exp(-dt * 6));   // ease toward the scroll target: smooth, frame-rate independent
  path.getPoint(shown, camera.position);
  camera.lookAt(target);
  product.rotation.y += dt * 0.4;
  const idx = Math.min(sections.length - 1, Math.floor(shown * sections.length));
  sections.forEach((s, i) => s.classList.toggle('on', i === idx));
  renderer.render(scene, camera);
});
window.__sc = { camera, get shown() { return shown; } };
</script>
</body>
</html>
```

## Juice helpers (verified: squash 1.28 at frame 4 then back to exactly 1, shake decays, easeOutBack(1) = 1)
Call `hit(mesh)` on land/pickup, `addShake(0.5)` on damage, `updateSquash(dt)` and `applyShake(camera, dt, time)` each frame AFTER the camera follow code.

```js
// easing helpers
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeOutBack = (t) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));   // frame-rate independent smoothing

// squash & stretch: call hit(mesh) on land / pickup; update every frame
const squash = new Map();
function hit(mesh, amount = 0.35) { squash.set(mesh, { t: 0, amount }); }
function updateSquash(dt) {
  for (const [mesh, s] of squash) {
    s.t += dt / 0.35;
    if (s.t >= 1) { mesh.scale.set(1, 1, 1); squash.delete(mesh); continue; }
    const k = Math.sin(s.t * Math.PI * 3) * (1 - s.t) * s.amount;   // decaying wobble
    mesh.scale.set(1 + k, 1 - k, 1 + k);
  }
}
// pop-in with overshoot (spawn, UI-like reveals)
function popIn(mesh, t) { mesh.scale.setScalar(easeOutBack(Math.min(t, 1))); }

// camera shake: add trauma on hits, it decays; offset the camera AFTER your follow logic
let trauma = 0;
const shakeOffset = new THREE.Vector3();
function addShake(v) { trauma = Math.min(1, trauma + v); }
function applyShake(camera, dt, time) {
  trauma = Math.max(0, trauma - dt * 1.5);
  const s = trauma * trauma * 0.35;                                  // squared = soft start, strong peak
  shakeOffset.set(Math.sin(time * 61) * s, Math.sin(time * 47 + 2) * s, 0);
  camera.position.add(shakeOffset);
}
// candle / neon flicker for point lights
function flicker(light, base, time) { light.intensity = base * (0.85 + 0.15 * Math.sin(time * 13) * Math.sin(time * 7.3)); }
```
