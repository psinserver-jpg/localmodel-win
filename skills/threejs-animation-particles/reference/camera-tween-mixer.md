---
name: camera-tween-mixer
description: Easing functions, own tween helper, GSAP via import map, procedural bob/sway/breathe, AnimationMixer crossfade, camera dolly/orbit/follow and a scroll-driven CatmullRom camera fly-through page.
triggers: [tween, 트윈, gsap, easing, 이징, ease, lerp, damp, camera, 카메라, fly-through, 플라이스루, scroll, 스크롤, catmullrom, path, 경로, mixer, animationmixer, crossfade, bobbing, sway, breathing, 흔들, 숨쉬기]
---
# Easing, tween, GSAP, procedural motion, AnimationMixer, scroll camera path

## Own tiny tween + easing (tested: reaches the end value, onDone fires)
```js
const ease = {
  linear: (t) => t,
  inOutQuad: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  outCubic: (t) => 1 - Math.pow(1 - t, 3),
  outBack: (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
  outElastic: (t) => (t === 0 || t === 1 ? t : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI) / 3) + 1),
  outBounce: (t) => { const n = 7.5625, d = 2.75; if (t < 1 / d) return n * t * t; if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75; if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375; return n * (t -= 2.625 / d) * t + 0.984375; },
};
const tweens = [];
function tween(target, to, duration, easing = ease.outCubic, onDone) {
  const from = {};
  for (const k in to) from[k] = target[k];
  const tw = { target, to, from, duration, easing, time: 0, onDone };
  tweens.push(tw);
  return tw;
}
function updateTweens(dt) {
  for (let i = tweens.length - 1; i >= 0; i--) {
    const tw = tweens[i];
    tw.time += dt;
    const k = tw.easing(Math.min(tw.time / tw.duration, 1));
    for (const key in tw.to) tw.target[key] = tw.from[key] + (tw.to[key] - tw.from[key]) * k;
    if (tw.time >= tw.duration) { tweens.splice(i, 1); if (tw.onDone) tw.onDone(); }
  }
}
// usage: tween(mesh.position, { x: 10, y: 0 }, 1, ease.outBack, () => console.log('done'));
// in the loop: updateTweens(dt);
```
GSAP (import map entry `"gsap": "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm"`): `import { gsap } from 'gsap'; gsap.to(mesh.position, { x: 5, duration: 1, ease: 'power2.out' });` `gsap.timeline().to(a, {...}).to(b, {...})`. Tween plain objects (`{fov: 60}`) and copy them to the camera inside the render loop, then `camera.updateProjectionMatrix()`. GSAP runs on its own ticker; it is fine next to your loop.

## Procedural motion (no clips needed)
```js
// fragment
const t = clock.elapsedTime;
float.position.y = baseY + Math.sin(t * 2) * 0.15;          // bobbing
tree.rotation.z = Math.sin(t * 1.2 + tree.userData.phase) * 0.04;  // swaying, phase per object
chest.scale.setScalar(1 + Math.sin(t * 2) * 0.03);           // breathing
leg.rotation.x = Math.sin(t * speed) * 0.8;                  // walk cycle (leg is a pivot Group)
mesh.rotation.y += dt * 0.8;                                 // spin
```

## AnimationMixer for GLTF clips (full page with buttons: `threejs-models-assets`)
```js
// fragment
const mixer = new THREE.AnimationMixer(model);
const actions = {};
gltf.animations.forEach((clip) => { actions[clip.name] = mixer.clipAction(clip); });
let current = actions['Idle'] || Object.values(actions)[0];
current.play();
function fadeTo(name, duration = 0.4) {
  const next = actions[name];
  if (!next || next === current) return;
  next.reset().setEffectiveTimeScale(1).setEffectiveWeight(1).fadeIn(duration).play();
  current.fadeOut(duration);
  current = next;
}
// one-shot clip: action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true;
// speed: action.timeScale = 1.5;   in the loop: mixer.update(dt);
```

## Camera moves
```js
// fragment
// dolly in:  camera.position.z = damp(camera.position.z, 4, 3, dt);
// orbit around a point automatically:
angle += dt * 0.3;
camera.position.set(cx + Math.cos(angle) * radius, height, cz + Math.sin(angle) * radius);
camera.lookAt(cx, 1, cz);
// follow with smoothing (third person):
const want = player.position.clone().add(new THREE.Vector3(0, 4, 8));
camera.position.x = damp(camera.position.x, want.x, 5, dt);
camera.position.y = damp(camera.position.y, want.y, 5, dt);
camera.position.z = damp(camera.position.z, want.z, 5, dt);
camera.lookAt(player.position.x, player.position.y + 1, player.position.z);
```

## Scroll-driven camera path (verified: camera x moved from -28 to 2.8 at progress 0.5; GSAP fov tween ran)
`CatmullRomCurve3` + `getPointAt(u)` (constant speed) + damped progress. Wheel and slider set `target`; `auto` button advances it.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>카메라 플라이스루</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#101826}canvas{display:block}
#ui{position:fixed;left:0;right:0;bottom:16px;display:flex;gap:10px;justify-content:center;align-items:center;font:600 15px system-ui,sans-serif;color:#fff}
#ui button{font:inherit;padding:8px 14px;border:0;border-radius:8px;background:#ffb703;color:#222;cursor:pointer}
#ui input{width:min(40vw,320px)}
#title{position:fixed;top:14px;left:16px;color:#fff;font:700 18px system-ui,sans-serif;text-shadow:0 1px 3px #000a;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","gsap":"https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm"}}</script>
</head>
<body>
<div id="title">스크롤 또는 슬라이더로 카메라를 따라가세요</div>
<div id="ui"><button id="auto">자동 재생</button><input id="bar" type="range" min="0" max="1" step="0.001" value="0"><button id="zoom">GSAP 줌</button></div>
<script type="module">
import * as THREE from 'three';
import { gsap } from 'gsap';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf6c89f);
scene.fog = new THREE.Fog(0xf6c89f, 20, 70);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 150);

scene.add(new THREE.HemisphereLight(0xffe2c4, 0x8a7a9a, 1.8));
const sun = new THREE.DirectionalLight(0xffd29a, 2.4);
sun.position.set(6, 12, 16);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30, near: 1, far: 70 });
sun.shadow.mapSize.set(2048, 2048);
scene.add(sun);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshStandardMaterial({ color: 0x8c7b6b }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// buildings on both sides of a winding road
const bm = new THREE.MeshStandardMaterial({ color: 0xe9d8c4, flatShading: true });
for (let i = 0; i < 70; i++) {
  const h = 2 + Math.random() * 7, w = 1.5 + Math.random() * 2;
  const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, w), bm.clone());
  b.material.color.offsetHSL(Math.random() * 0.08 - 0.04, 0, Math.random() * 0.1 - 0.05);
  b.position.set(-30 + i * 0.85 + Math.random() * 3, h / 2, (i % 2 ? 1 : -1) * (5 + Math.random() * 8) - 10);
  b.castShadow = b.receiveShadow = true;
  scene.add(b);
}

// camera path: smooth spline through points, look-at path slightly ahead on the same curve
const path = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-28, 2.2, 6), new THREE.Vector3(-14, 2.5, -2), new THREE.Vector3(-2, 3, -12),
  new THREE.Vector3(10, 2.2, -8), new THREE.Vector3(22, 4, -14), new THREE.Vector3(30, 8, -2),
], false, 'catmullrom', 0.5);
const road = new THREE.Mesh(new THREE.TubeGeometry(path, 120, 0.05, 4), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35 }));
road.position.y = -2.1;
scene.add(road);

const damp = (a, b, lambda, dt) => THREE.MathUtils.lerp(a, b, 1 - Math.exp(-lambda * dt));   // frame-rate independent smoothing
const state = { target: 0, current: 0, auto: false };
const bar = document.getElementById('bar');
bar.addEventListener('input', () => { state.target = Number(bar.value); });
window.addEventListener('wheel', (e) => { state.target = THREE.MathUtils.clamp(state.target + e.deltaY * 0.0004, 0, 1); bar.value = state.target; }, { passive: true });
document.getElementById('auto').onclick = () => { state.auto = !state.auto; };
const fovObj = { fov: 60 };
document.getElementById('zoom').onclick = () => {
  gsap.timeline().to(fovObj, { fov: 35, duration: 0.8, ease: 'power2.out' }).to(fovObj, { fov: 60, duration: 1, ease: 'elastic.out(1,0.5)' });
};

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
const pos = new THREE.Vector3(), look = new THREE.Vector3();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  if (state.auto) { state.target = Math.min(1, state.target + dt * 0.04); bar.value = state.target; }
  state.current = damp(state.current, state.target, 4, dt);          // camera eases toward the scroll target
  path.getPointAt(state.current, pos);                                // getPointAt = constant speed along the curve
  path.getPointAt(Math.min(1, state.current + 0.03), look);
  camera.position.copy(pos);
  camera.position.y += Math.sin(clock.elapsedTime * 2) * 0.03;       // subtle handheld bob
  camera.lookAt(look);
  camera.fov = fovObj.fov;
  camera.updateProjectionMatrix();
  renderer.render(scene, camera);
}
animate();
window.__t = { state, camera, fovObj };
</script>
</body>
</html>
```
