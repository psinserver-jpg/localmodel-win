---
name: particles
description: Complete particle fountain with click-to-burst fireworks, a reusable ring-buffer Particles class, additive soft sprites and screen shake. Verified in a browser.
triggers: [particles, particle, 파티클, fountain, 분수, burst, 폭죽, firework, explosion, 폭발, sparks, 불꽃, points, pointsmaterial, additive, screen shake, trail]
---
# Particle fountain + burst (verified: 420 fountain particles alive, 220 on burst, no errors)

Copy as `index.html`. `Particles` is reusable: `new Particles(max, size, texture)`, `emit(x,y,z,vx,vy,vz,color,life)`, `update(dt, gravity)`. Ideas: make a trail by emitting at a moving object each frame; make smoke with normal blending, upward velocity and growing size via a second material; change `gravity` to positive for rising embers.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>파티클 분수</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#05060d}canvas{display:block}
#hud{position:fixed;top:14px;left:16px;color:#fff;font:600 16px/1.5 system-ui,sans-serif;text-shadow:0 1px 3px #000a;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">클릭하면 폭죽이 터져요 · 드래그로 회전</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05060d);
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 4, 11);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 3, 0);
controls.enableDamping = true;

// soft round sprite drawn on a canvas (no image file needed)
function softDot() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.4, 'rgba(255,255,255,0.5)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Particle system: ONE Points object, typed arrays allocated once, dead particles are recycled
class Particles {
  constructor(max, size, tex) {
    this.max = max;
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.vel = new Float32Array(max * 3);
    this.life = new Float32Array(max);      // seconds left, <= 0 = free slot
    this.maxLife = new Float32Array(max).fill(1);
    this.base = new Float32Array(max * 3);  // colour at birth
    this.next = 0;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(this.col, 3));
    const mat = new THREE.PointsMaterial({ size, map: tex, vertexColors: true, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true });
    this.points = new THREE.Points(geo, mat);
    this.points.frustumCulled = false;      // positions change every frame, bounding sphere would be stale
    this.pos.fill(9999);                    // park unused particles far away
  }
  emit(x, y, z, vx, vy, vz, color, life) {
    const i = this.next;
    this.next = (this.next + 1) % this.max; // ring buffer: overwrite the oldest
    this.pos.set([x, y, z], i * 3);
    this.vel.set([vx, vy, vz], i * 3);
    this.base.set([color.r, color.g, color.b], i * 3);
    this.life[i] = this.maxLife[i] = life;
  }
  update(dt, gravity) {
    for (let i = 0; i < this.max; i++) {
      if (this.life[i] <= 0) continue;
      this.life[i] -= dt;
      const k = i * 3;
      if (this.life[i] <= 0) { this.pos[k + 1] = 9999; this.col[k] = this.col[k + 1] = this.col[k + 2] = 0; continue; }
      this.vel[k + 1] += gravity * dt;
      this.pos[k] += this.vel[k] * dt;
      this.pos[k + 1] += this.vel[k + 1] * dt;
      this.pos[k + 2] += this.vel[k + 2] * dt;
      const f = this.life[i] / this.maxLife[i];   // fade out by darkening (additive blending)
      this.col[k] = this.base[k] * f; this.col[k + 1] = this.base[k + 1] * f; this.col[k + 2] = this.base[k + 2] * f;
    }
    this.points.geometry.attributes.position.needsUpdate = true;
    this.points.geometry.attributes.color.needsUpdate = true;
  }
}

const tex = softDot();
const fountain = new Particles(4000, 0.22, tex);
const sparks = new Particles(3000, 0.3, tex);
scene.add(fountain.points, sparks.points);

const floor = new THREE.Mesh(new THREE.CircleGeometry(8, 48), new THREE.MeshBasicMaterial({ color: 0x0c1020 }));
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

const tmp = new THREE.Color();
function burst(x, y, z, hue) {
  for (let n = 0; n < 220; n++) {
    const a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1), s = 2 + Math.random() * 5;
    tmp.setHSL(hue + Math.random() * 0.08, 1, 0.6);
    sparks.emit(x, y, z, Math.sin(b) * Math.cos(a) * s, Math.cos(b) * s, Math.sin(b) * Math.sin(a) * s, tmp, 0.8 + Math.random() * 0.8);
  }
}
let shake = 0;
renderer.domElement.addEventListener('pointerdown', () => {
  burst((Math.random() - 0.5) * 6, 5 + Math.random() * 3, (Math.random() - 0.5) * 4, Math.random());
  shake = 0.4;
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
let t = 0, emitAcc = 0;
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  t += dt;
  emitAcc += dt * 600;                       // 600 particles per second, independent of frame rate
  while (emitAcc >= 1) {
    emitAcc -= 1;
    const a = Math.random() * Math.PI * 2, s = Math.random() * 1.2;
    tmp.setHSL(0.55 + 0.1 * Math.sin(t), 0.9, 0.6);
    fountain.emit(0, 0.1, 0, Math.cos(a) * s, 8 + Math.random() * 2.5, Math.sin(a) * s, tmp, 1.6 + Math.random() * 0.6);
  }
  fountain.update(dt, -9.8);
  sparks.update(dt, -6);
  controls.update();
  const off = shake > 0 ? shake : 0;         // screen shake: random offset that decays, applied after controls
  shake = Math.max(0, shake - dt * 1.5);
  camera.position.x += (Math.random() - 0.5) * off * 0.3;
  camera.position.y += (Math.random() - 0.5) * off * 0.3;
  renderer.render(scene, camera);
}
animate();
window.__t = { fountain, sparks, burst, alive: (p) => p.life.reduce((n, l) => n + (l > 0 ? 1 : 0), 0) };
</script>
</body>
</html>
```
