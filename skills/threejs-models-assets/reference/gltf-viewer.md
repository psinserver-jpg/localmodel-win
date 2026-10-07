---
name: gltf-viewer
description: Load a GLB with GLTFLoader and LoadingManager, progress bar, fallback model on failure, fit/centre with bone-based measuring, shadows, AnimationMixer clip buttons with crossfade and one-shot clips. Verified with RobotExpressive.glb.
triggers: [gltf, glb, gltfloader, loadingmanager, 모델 불러오기, 로더, loader, animation, 애니메이션, clip, mixer, animationmixer, crossfade, box3, fit, scale, draco, fallback, texture, textureloader, robotexpressive, viewer, 뷰어]
---
# GLB viewer with animation buttons (verified: loaded 14 clips, time advances, Wave returns to Idle, failed URL shows fallback)

Swap `MODEL_URL` for another verified model (`Soldier.glb` verified: clips Idle/Run/TPose/Walk, textured, faces away from the camera so set `model.rotation.y = Math.PI`; `Xbot.glb`, `Horse.glb`, `Flamingo.glb`, `Parrot.glb` exist, clip names unverified - always build buttons from `gltf.animations`). Names in `oneShot` only matter if the model has them. Texture example: `const tex = new THREE.TextureLoader(manager).load(url); tex.colorSpace = THREE.SRGBColorSpace;`. Draco: `import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'; const d = new DRACOLoader(); d.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/libs/draco/'); loader.setDRACOLoader(d);`.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>로봇 모델 뷰어</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#1b2230}canvas{display:block}
#bar{position:fixed;left:0;right:0;bottom:14px;display:flex;flex-wrap:wrap;gap:6px;justify-content:center;padding:0 10px}
#bar button{font:600 14px system-ui,sans-serif;padding:7px 12px;border:0;border-radius:8px;background:#e6edf7;color:#1b2230;cursor:pointer}
#bar button.on{background:#ffb703}
#msg{position:fixed;inset:0;display:grid;place-items:center;color:#fff;font:700 20px system-ui,sans-serif;pointer-events:none}
#msg i{display:block;height:6px;width:200px;background:#ffffff33;border-radius:3px;margin-top:10px;overflow:hidden}
#msg b{display:block;height:100%;width:0;background:#ffb703}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="msg"><div>모델 불러오는 중...<i><b id="prog"></b></i></div></div>
<div id="bar"></div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_URL = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/models/gltf/RobotExpressive/RobotExpressive.glb';
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1b2230);
scene.fog = new THREE.Fog(0x1b2230, 15, 40);
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.8, 7);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.1, 0);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x35324a, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(4, 8, 5);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 25 });
scene.add(sun);
const floor = new THREE.Mesh(new THREE.CircleGeometry(12, 48), new THREE.MeshStandardMaterial({ color: 0x2c3548, roughness: 0.9 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

// fallback shown if the download fails (offline, blocked): a primitive robot, so the page is never empty
function fallbackRobot() {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color: 0x4f8cff, flatShading: true });
  const body = new THREE.Mesh(new THREE.BoxGeometry(1, 1.4, 0.6), m);
  body.position.y = 1.2;
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.6, 0.6), m);
  head.position.y = 2.2;
  g.add(body, head);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

// bounding box that is also right for skinned (rigged) models: Box3.setFromObject can be 50x too big for them,
// so measure the bone positions instead when there are bones
function measure(model) {
  model.updateMatrixWorld(true);
  const box = new THREE.Box3();
  const v = new THREE.Vector3();
  let bones = 0;
  model.traverse((o) => { if (o.isBone) { box.expandByPoint(o.getWorldPosition(v)); bones++; } });
  return bones > 1 ? box : box.setFromObject(model);
}
// scale to a target height, stand it on y = 0 and centre it in x/z
function fitModel(model, targetHeight = 2.5) {
  let box = measure(model);
  model.scale.multiplyScalar(targetHeight / box.getSize(new THREE.Vector3()).y);
  box = measure(model);
  const c = box.getCenter(new THREE.Vector3());
  model.position.x -= c.x;
  model.position.z -= c.z;
  model.position.y -= box.min.y;
}

let mixer = null, actions = {}, current = null;
const bar = document.getElementById('bar');
function fadeTo(name, duration = 0.4) {
  const next = actions[name];
  if (!next || next === current) return;
  next.reset().setEffectiveTimeScale(1).setEffectiveWeight(1).fadeIn(duration).play();
  if (current) current.fadeOut(duration);
  current = next;
  [...bar.children].forEach((b) => b.classList.toggle('on', b.textContent === name));
}

const manager = new THREE.LoadingManager();
manager.onProgress = (url, loaded, total) => {
  const p = document.getElementById('prog');
  if (p) p.style.width = (loaded / total * 100) + '%';
};
const loader = new GLTFLoader(manager);
loader.load(MODEL_URL, (gltf) => {
  const model = gltf.scene;
  model.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  fitModel(model, 2.0);
  scene.add(model);
  mixer = new THREE.AnimationMixer(model);
  gltf.animations.forEach((clip) => {
    actions[clip.name] = mixer.clipAction(clip);
    const b = document.createElement('button');
    b.textContent = clip.name;
    b.onclick = () => fadeTo(clip.name);
    bar.appendChild(b);
  });
  const oneShot = ['Jump', 'Yes', 'No', 'Wave', 'Punch', 'ThumbsUp'];   // play once, then return to Idle
  oneShot.forEach((n) => { if (actions[n]) { actions[n].setLoop(THREE.LoopOnce, 1); actions[n].clampWhenFinished = true; } });
  mixer.addEventListener('finished', () => fadeTo('Idle'));
  fadeTo('Idle');
  document.getElementById('msg').remove();
}, undefined, (err) => {
  console.warn('모델 로딩 실패, 기본 로봇으로 대체합니다:', err && err.message);
  scene.add(fallbackRobot());
  document.getElementById('msg').textContent = '모델을 불러오지 못해 기본 모델을 보여줘요';
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  if (mixer) mixer.update(dt);
  controls.update();
  renderer.render(scene, camera);
}
animate();
window.__t = { get names() { return Object.keys(actions); }, get current() { return current && current.getClip().name; }, fadeTo, get time() { return current ? current.time : -1; } };
</script>
</body>
</html>
```
