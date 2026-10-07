---
name: boilerplate
description: three.js import list for common addons, HUD overlay, loading screen, resize/fullscreen/mobile handling, on-demand rendering, and splitting into files with a local server.
triggers: [import, addons, hud, overlay, loading screen, fullscreen, mobile, resize, setanimationloop, local server, http.server, split files, css2drenderer, label, 로딩 화면, 전체화면, 모바일, 오버레이, 라벨, 파일 분리, 로컬 서버]
---
# three.js boilerplate variants

## Import cheat-sheet (all with the import map from SKILL.md)
```js
// fragment
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import * as BufferGeometryUtils from 'three/addons/utils/BufferGeometryUtils.js';
```
Extra libraries go in the same import map, e.g. `"cannon-es": "https://cdn.jsdelivr.net/npm/cannon-es@0.20.0/dist/cannon-es.js"` and `"gsap": "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm"`.

## HTML overlay (score, buttons, messages) on top of the canvas
```html
<div id="hud" style="position:fixed;inset:0;pointer-events:none;font:600 20px/1.4 system-ui,'Pretendard',sans-serif;color:#fff;text-shadow:0 1px 3px #0008">
  <div id="score" style="position:absolute;top:16px;left:20px">점수 0</div>
  <div id="msg" style="position:absolute;inset:0;display:grid;place-items:center;text-align:center">스페이스바 또는 화면을 눌러 시작</div>
</div>
```
```js
const scoreEl = document.getElementById('score');
function setScore(n) { scoreEl.textContent = '점수 ' + Math.floor(n); }
```
Use `pointer-events:none` on the HUD container and `pointer-events:auto` on buttons only, so the canvas still gets input.

## Resize that also handles phones rotating
```js
function onResize() {
  const w = window.innerWidth, h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
}
window.addEventListener('resize', onResize);
window.addEventListener('orientationchange', onResize);
```
For a wide scene on narrow screens widen the view: `camera.fov = w / h < 1 ? 75 : 55;` before `updateProjectionMatrix()`.

## Loading screen with progress (for GLTF/textures)
```js
const manager = new THREE.LoadingManager();
const bar = document.getElementById('bar');
manager.onProgress = (url, loaded, total) => { bar.style.width = (loaded / total * 100) + '%'; };
manager.onLoad = () => { document.getElementById('loading').remove(); start(); };
manager.onError = (url) => console.warn('불러오기 실패:', url);
const textures = new THREE.TextureLoader(manager);
function start() { animate(); }
```

## Render only when needed (static scenes, saves battery)
```js
let dirty = true;
controls.addEventListener('change', () => { dirty = true; });
function frame() {
  requestAnimationFrame(frame);
  if (!dirty) return;
  dirty = false;
  renderer.render(scene, camera);
}
frame();
```

## HTML labels attached to 3D points
```js
const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.cssText = 'position:fixed;top:0;left:0;pointer-events:none';
document.body.appendChild(labelRenderer.domElement);
const div = document.createElement('div');
div.textContent = '입구';
div.style.cssText = 'padding:4px 8px;border-radius:6px;background:#000a;color:#fff;font:12px system-ui';
const label = new CSS2DObject(div);
label.position.set(0, 2, 0);
scene.add(label);
// in the loop, after renderer.render(): labelRenderer.render(scene, camera);
```

## Splitting into files (needs a server, never file://)
Start `python3 -m http.server 8000` in the project folder (or the `serve` tool) and open `http://localhost:8000/`. Then `<script type="module" src="./main.js"></script>` and `import { Player } from './player.js';` work. Tell the user the URL to open.

## Typical project layout when files are split
```text
index.html      page, import map, HUD markup
main.js         renderer, scene, loop
world.js        ground, lights, sky, decorations
player.js       the controllable object
enemies.js      spawners and obstacles
```

## Tab hidden / resume without a time jump
```js
document.addEventListener('visibilitychange', () => { if (!document.hidden) clock.getDelta(); });
```
