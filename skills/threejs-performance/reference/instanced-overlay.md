---
name: instanced-overlay
description: Complete working page: 5000 animated cubes in ONE InstancedMesh (1 draw call), reused temp objects, a live FPS / draw-call / triangle / memory overlay from renderer.info, and pausing on a hidden tab.
triggers: [fps overlay, fps 표시, stats overlay, renderer.info, draw call counter, 드로우콜 확인, instancedmesh example, 인스턴스 예제, 5000 cubes, 큐브 수천개, 성능 측정, benchmark]
---
# Instanced cubes + stats overlay (verified: 1 draw call, 60000 triangles)
The overlay needs no library: count frames, read `renderer.info` every 0.5 s. In the harness (software WebGL) FPS was 20 only because there is no GPU; the numbers that matter are `calls: 1` and the single geometry. If the page is slow on a real device, first lower `COUNT`, then pixel ratio, then cube segments.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>성능 데모</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#0d1117}canvas{display:block}#stats{position:fixed;right:10px;top:10px;padding:6px 10px;background:#000a;color:#8f8;font:12px/1.5 monospace;border-radius:6px;white-space:pre}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="stats"></div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));   // phones: 1.5 or even 1 is plenty
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);
scene.fog = new THREE.Fog(0x0d1117, 30, 80);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 18, 34);
camera.lookAt(0, 0, 0);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x334455, 1.4));
const sun = new THREE.DirectionalLight(0xffffff, 2);
sun.position.set(5, 10, 7);
scene.add(sun);

// 5000 cubes = 1 geometry + 1 material + 1 draw call
const COUNT = 5000, GRID = 71;
const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(0.7, 0.7, 0.7), new THREE.MeshLambertMaterial({ color: 0xffffff }), COUNT);
mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);   // we rewrite it every frame
const base = new Float32Array(COUNT * 2);
const color = new THREE.Color();
for (let i = 0; i < COUNT; i++) {
  const x = (i % GRID - GRID / 2) * 0.9, z = (Math.floor(i / GRID) - GRID / 2) * 0.9;
  base[i * 2] = x; base[i * 2 + 1] = z;
  mesh.setColorAt(i, color.setHSL(0.55 + (x + z) * 0.004, 0.7, 0.55));
}
scene.add(mesh);

// reuse temp objects: no `new` inside the loop
const m4 = new THREE.Matrix4(), pos = new THREE.Vector3(), quat = new THREE.Quaternion(), scl = new THREE.Vector3(1, 1, 1), axis = new THREE.Vector3(0, 1, 0);

const el = document.getElementById('stats');
let frames = 0, acc = 0, fps = 0;
function updateStats(dt) {
  frames++; acc += dt;
  if (acc >= 0.5) {
    fps = Math.round(frames / acc); frames = 0; acc = 0;
    const i = renderer.info;
    el.textContent = 'FPS ' + fps + '\n호출 ' + i.render.calls + '\n삼각형 ' + i.render.triangles + '\n지오메트리 ' + i.memory.geometries + ' 텍스처 ' + i.memory.textures;
  }
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
// pause when the tab is hidden: the clock delta would otherwise be huge on return (we also clamp it)
let running = true;
document.addEventListener('visibilitychange', () => { running = !document.hidden; });
const clock = new THREE.Clock();
let t = 0;
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  if (!running) return;
  t += dt;
  for (let i = 0; i < COUNT; i++) {
    const x = base[i * 2], z = base[i * 2 + 1];
    pos.set(x, Math.sin(x * 0.3 + t * 2) * Math.cos(z * 0.3 + t * 1.5) * 2, z);
    quat.setFromAxisAngle(axis, t + x * 0.1);
    mesh.setMatrixAt(i, m4.compose(pos, quat, scl));
  }
  mesh.instanceMatrix.needsUpdate = true;
  mesh.computeBoundingSphere();   // r160: cull against the real extent
  renderer.render(scene, camera);
  updateStats(dt);
});
window.__p = { renderer, get fps() { return fps; } };
</script>
</body>
</html>
```

## When something is slow, check in this order
1. `calls` high -> instancing/merging. 2. `triangles` high -> fewer segments, LOD. 3. FPS low with low calls/triangles -> pixel ratio, shadows, transparent overdraw, postprocessing. 4. Stutter every few seconds -> allocation in the loop (GC) or texture upload.
