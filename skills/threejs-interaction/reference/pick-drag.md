---
name: pick-drag
description: Raycaster picking page: hover highlight and tooltip, click select with a CSS2D label, drag objects on a ground plane with OrbitControls disabled meanwhile, and lil-gui controls. Verified with simulated pointer events.
triggers: [pick, picking, raycaster, 레이캐스트, 선택, select, hover, 호버, drag, 드래그, tooltip, 툴팁, css2drenderer, label, 라벨, lil-gui, gui, 슬라이더, click, 클릭, orbitcontrols, 하이라이트, highlight]
---
# Pick, highlight, drag, label, GUI (verified: hover found the sphere, click selected it, drag moved it 2.8 m, label shown, no errors)

For loaded GLTF models put the model root in `items` (`intersectObjects(items, true)` already searches children and the code climbs back to the root); to highlight a model change materials in `traverse` instead of `o.material.emissive` directly. Touch works unchanged because it uses pointer events. For a click that must not count after an orbit drag, compare `pointerdown` and `pointerup` positions (< 5 px).

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>선택과 드래그</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#1d2433;touch-action:none}canvas{display:block}
#tip{position:fixed;pointer-events:none;padding:5px 9px;border-radius:6px;background:#000c;color:#fff;font:600 13px system-ui,sans-serif;display:none;white-space:nowrap}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #0007;pointer-events:none}
.label{white-space:nowrap;padding:3px 8px;border-radius:6px;background:#ffb703;color:#222;font:700 13px system-ui,sans-serif}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/","lil-gui":"https://cdn.jsdelivr.net/npm/lil-gui@0.19/+esm"}}</script>
</head>
<body>
<div id="hud">물체에 마우스를 올리고, 클릭해서 선택, 끌어서 이동 · 빈 곳은 드래그로 회전</div>
<div id="tip"></div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import GUI from 'lil-gui';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.cssText = 'position:fixed;top:0;left:0;pointer-events:none';
document.body.appendChild(labelRenderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1d2433);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(6, 6, 9);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 4;
controls.maxDistance = 25;
controls.maxPolarAngle = Math.PI * 0.49;     // never go under the floor
controls.target.set(0, 0.5, 0);

scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x35324a, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(5, 9, 6);
sun.castShadow = true;
Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 30 });
scene.add(sun);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({ color: 0x2d3650 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);                             // not in `items`, so it is never picked

// pickable things
const items = [];
const defs = [['상자', 0xff7043, 'box'], ['공', 0x42a5f5, 'sphere'], ['원뿔', 0x66bb6a, 'cone'], ['도넛', 0xab47bc, 'torus'], ['원기둥', 0xffca28, 'cyl']];
defs.forEach(([name, color, kind], i) => {
  const geo = { box: new THREE.BoxGeometry(1.2, 1.2, 1.2), sphere: new THREE.SphereGeometry(0.7, 24, 16), cone: new THREE.ConeGeometry(0.7, 1.4, 20),
    torus: new THREE.TorusGeometry(0.5, 0.22, 12, 32), cyl: new THREE.CylinderGeometry(0.55, 0.55, 1.3, 20) }[kind];
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.5 }));
  m.position.set(-5 + i * 2.5, 0.8, (i % 2) * 2 - 1);
  m.castShadow = true;
  m.userData.name = name;                     // data lives on the mesh
  scene.add(m);
  items.push(m);
});

// ---- picking ----
const raycaster = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const tip = document.getElementById('tip');
function pick(e) {
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);   // pixels -> -1..1, Y flipped
  raycaster.setFromCamera(ndc, camera);
  const hit = raycaster.intersectObjects(items, true)[0];      // true = look into children (loaded models)
  if (!hit) return null;
  let o = hit.object;
  while (o.parent && !items.includes(o)) o = o.parent;          // climb to the root that is in `items`
  return { object: o, point: hit.point };
}
let hovered = null, selected = null, dragging = null;
const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), dragPoint = new THREE.Vector3(), dragOffset = new THREE.Vector3();
const label = new CSS2DObject(Object.assign(document.createElement('div'), { className: 'label' }));
function setEmissive(o, v) { if (o) o.material.emissive.setHex(v); }

renderer.domElement.addEventListener('pointermove', (e) => {
  if (dragging) {
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    if (raycaster.ray.intersectPlane(dragPlane, dragPoint)) {
      dragging.position.x = dragPoint.x + dragOffset.x;
      dragging.position.z = dragPoint.z + dragOffset.z;
    }
    return;
  }
  const h = pick(e);
  const next = h ? h.object : null;
  if (next !== hovered) {
    if (hovered !== selected) setEmissive(hovered, 0x000000);
    hovered = next;
    if (hovered !== selected) setEmissive(hovered, 0x333333);
    renderer.domElement.style.cursor = hovered ? 'pointer' : 'default';
  }
  tip.style.display = hovered ? 'block' : 'none';
  if (hovered) { tip.textContent = hovered.userData.name; tip.style.left = e.clientX + 14 + 'px'; tip.style.top = e.clientY + 14 + 'px'; }
});
renderer.domElement.addEventListener('pointerdown', (e) => {
  const h = pick(e);
  if (selected && selected !== (h && h.object)) { setEmissive(selected, 0x000000); selected.remove(label); selected = null; }
  if (!h) return;
  selected = h.object;
  setEmissive(selected, 0x666600);
  label.element.textContent = selected.userData.name + ' 선택됨';
  label.position.set(0, 1.3, 0);
  selected.add(label);
  dragging = selected;
  dragPlane.constant = -selected.position.y;                   // plane at the object's height
  raycaster.ray.intersectPlane(dragPlane, dragPoint);
  dragOffset.copy(selected.position).sub(dragPoint);
  dragOffset.y = 0;
  controls.enabled = false;                                    // do not orbit while dragging
  renderer.domElement.setPointerCapture(e.pointerId);
});
function endDrag() { dragging = null; controls.enabled = true; }
renderer.domElement.addEventListener('pointerup', endDrag);
renderer.domElement.addEventListener('pointercancel', endDrag);

// ---- GUI: sliders/checkboxes change the scene ----
const params = { autoRotate: false, 크기: 1, 색: '#ff7043' };
const gui = new GUI({ title: '설정' });
gui.add(params, 'autoRotate').name('자동 회전').onChange((v) => { controls.autoRotate = v; });
gui.add(params, '크기', 0.5, 2, 0.05).onChange((v) => { if (selected) selected.scale.setScalar(v); });
gui.addColor(params, '색').onChange((v) => { if (selected) selected.material.color.set(v); });

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  labelRenderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  items.forEach((m, i) => { if (m !== dragging) m.rotation.y += dt * 0.4 * (i % 2 ? 1 : -1); });
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}
animate();
// test hook: where is an item on screen?
window.__t = { items, camera, renderer, get selected() { return selected; }, get hovered() { return hovered; },
  screen(o) { const v = o.position.clone().project(camera); return { x: (v.x + 1) / 2 * innerWidth, y: (1 - v.y) / 2 * innerHeight }; } };
</script>
</body>
</html>
```
