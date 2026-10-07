---
name: threejs-basics
description: Set up and run three.js (WebGL) 3D scenes that actually work on first try - single-file HTML, correct CDN imports, renderer/scene/camera/lights/loop/resize, and a black-screen debugging checklist. Use for any three.js, WebGL or 3D web request.
triggers: [three.js, threejs, three js, webgl, 3d, 3d scene, 3d web, 3d website, 3d viewer, 3d model viewer, 3d graphics, scene, camera, renderer, mesh, geometry, orbitcontrols, perspectivecamera, 쓰리js, 쓰리제이에스, 3차원, 3d 웹, 3d 웹사이트, 3d 장면, 3d 뷰어, 3d 그래픽, 3d 만들어, 입체, 웹gl]
priority: 56
---
# three.js basics (use r160, always)

## Hard rules
1. Deliver ONE `index.html`: CSS in `<style>`, JS in an inline `<script type="module">`. It runs by double-click (file://). **External module files (`main.js`) are blocked on file://** - only split files if you also start a local server (the `serve` tool, or `python3 -m http.server 8000`).
2. Load three with an import map in `<head>` BEFORE the module script, pinned to one version. Addons (`three/addons/...`) must be the SAME version as core:
```html
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
```
3. NEVER use `<script src=".../three.min.js">` or `build/three.js` (removed in r160), `THREE.Geometry` (removed; use BufferGeometry), `renderer.gammaOutput` (use `renderer.outputColorSpace = THREE.SRGBColorSpace`).
4. Always do: renderer (pixelRatio capped at 2) -> scene -> camera -> LIGHTS -> objects -> resize handler -> animate loop with `THREE.Clock` -> `renderer.render`. Standard/Phong/Lambert materials are BLACK without lights.
5. Animate with `dt` seconds (`clock.getDelta()`, clamp to 0.05), never with per-frame constants.
6. Units = meters, +Y up, camera looks down -Z, angles in radians. A plane lies flat after `rotation.x = -Math.PI / 2`.
7. Write all UI text in the user's language. Put HUD/buttons in HTML over the canvas (`position:fixed`), not in 3D.
8. Finish: no console errors, something visible and moving, controls explained on screen.

## Working template (verified)
```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3D 장면</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#0b0d10}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
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
scene.background = new THREE.Color(0x87ceeb);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(4, 3, 6);

scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 2.0);
sun.position.set(5, 8, 4);
sun.castShadow = true;
scene.add(sun);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ color: 0x4caf50 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

const cube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: 0xff7043 }));
cube.position.y = 0.5;
cube.castShadow = true;
scene.add(cube);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  cube.rotation.y += dt;
  controls.update();
  renderer.render(scene, camera);
}
animate();
</script>
</body>
</html>
```

## Black / empty screen checklist (check in this order)
1. Browser console: "Failed to resolve module specifier 'three'" -> import map missing or placed after the module script. "CORS"/"Cross-Origin" on file:// -> you used an external module file; inline it or run a server.
2. No lights (or light intensity 0) with a Standard/Phong/Lambert material. Use MeshBasicMaterial to test.
3. Camera inside the object, looking away, or `near/far` wrong. Set `camera.position.set(0, 2, 6); camera.lookAt(0, 1, 0)`.
4. Forgot `scene.add(mesh)` or `renderer.render(scene, camera)` in the loop.
5. Canvas size 0 (parent has no height) -> use `window.innerWidth/innerHeight`.
6. Single-sided plane seen from behind: `side: THREE.DoubleSide`.
7. Light intensities (r155+ physical units): Directional 1-3, Hemisphere/Ambient 0.3-1.5, Point/Spot 30-300 (they fall off with distance).

## Also see
Game structure -> `threejs-game`. Lights/materials -> `threejs-materials-lighting`. Models/GLTF -> `threejs-models-assets`. Mouse/keys -> `threejs-interaction`.
