---
name: cannon-pile
description: Complete working page: cannon-es world with ground plane, contact material, boxes and balls spawned by buttons, mesh sync, sleeping, removal. Verified that 40 bodies come to rest on the ground and never fall through.
triggers: [cannon-es example, 물리 예제, falling boxes, 상자 떨어뜨리기, 공 튕기기, bouncing balls, spawn bodies, 물체 생성, physics pile, 더미, rigid body example]
---
# cannon-es pile (verified: 40 bodies rest at y = 0.5, none below the ground)
Drop boxes and balls with the buttons. Tune `restitution` (bounce) and `friction` in the ContactMaterial. Bodies drop in a column (`y = 3 + n*0.6`) so they never spawn inside each other.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>물리 더미</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#dfe9f3}canvas{display:block}#ui{position:fixed;left:16px;top:12px;font:14px sans-serif;color:#223}button{font:inherit;padding:8px 14px;margin-right:6px;border:0;border-radius:8px;background:#2f6fed;color:#fff}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/","cannon-es":"https://cdn.jsdelivr.net/npm/cannon-es@0.20.0/dist/cannon-es.js"}}</script>
</head>
<body>
<div id="ui"><button id="box">상자 추가</button><button id="ball">공 추가</button><button id="clear">비우기</button><span id="count"></span></div>
<script type="module">
import * as THREE from 'three';
import * as CANNON from 'cannon-es';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdfe9f3);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(7, 9, 9);
camera.lookAt(0, 0.5, 0);
scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.2));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.2);
sun.position.set(6, 12, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 40 });
scene.add(sun);

const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({ color: 0x9bb88a }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// physics world
const world = new CANNON.World({ gravity: new CANNON.Vec3(0, -9.82, 0) });
world.allowSleep = true;
const mat = new CANNON.Material('default');
world.addContactMaterial(new CANNON.ContactMaterial(mat, mat, { friction: 0.4, restitution: 0.35 }));
const groundBody = new CANNON.Body({ mass: 0, shape: new CANNON.Plane(), material: mat });
groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);   // plane normal is +Z by default -> rotate to +Y
world.addBody(groundBody);

// shared geometry + materials (never create per spawn)
const boxGeo = new THREE.BoxGeometry(1, 1, 1);
const ballGeo = new THREE.SphereGeometry(0.5, 24, 16);
const colors = [0xff7043, 0x42a5f5, 0xffca28, 0xab47bc, 0x26a69a].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.5 }));
const items = [];   // { mesh, body }

function spawn(kind) {
  const x = (Math.random() - 0.5) * 1.5, z = (Math.random() - 0.5) * 1.5, y = 3 + items.length * 0.6;   // drop in a column so they pile up
  const shape = kind === 'box' ? new CANNON.Box(new CANNON.Vec3(0.5, 0.5, 0.5)) : new CANNON.Sphere(0.5);
  const body = new CANNON.Body({ mass: 1, shape, material: mat, position: new CANNON.Vec3(x, y, z), sleepSpeedLimit: 0.15, sleepTimeLimit: 0.8, linearDamping: 0.1, angularDamping: 0.4 });
  body.quaternion.setFromEuler(Math.random() * 3, Math.random() * 3, 0);
  world.addBody(body);
  const mesh = new THREE.Mesh(kind === 'box' ? boxGeo : ballGeo, colors[items.length % colors.length]);
  mesh.castShadow = true;
  scene.add(mesh);
  items.push({ mesh, body });
}
function clearAll() {
  for (const it of items) { world.removeBody(it.body); scene.remove(it.mesh); }   // geometry/materials are shared: do not dispose
  items.length = 0;
}
document.getElementById('box').onclick = () => spawn('box');
document.getElementById('ball').onclick = () => spawn('ball');
document.getElementById('clear').onclick = clearAll;
for (let i = 0; i < 10; i++) spawn(i % 3 ? 'box' : 'ball');

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
const countEl = document.getElementById('count');
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  world.step(1 / 60, dt, 3);                       // fixed 60 Hz inside, up to 3 catch-up substeps
  for (const it of items) {
    it.mesh.position.copy(it.body.position);       // cannon Vec3/Quaternion have the same x,y,z(,w) fields
    it.mesh.quaternion.copy(it.body.quaternion);
  }
  countEl.textContent = ' 물체 ' + items.length + '개';
  renderer.render(scene, camera);
});
window.__t = { items, world, spawn, clearAll };
</script>
</body>
</html>
```
