---
name: synthwave
description: Complete working page: neon synthwave scene - striped sun disc in a sky-dome shader, scrolling neon grid floor shader with distance fade, dark mountains with glowing edges, UnrealBloomPass with HDR colours, CSS neon title.
triggers: [synthwave example, 신스웨이브, vaporwave, 베이퍼웨이브, retro grid, 레트로 그리드, neon sunset, 네온 석양, outrun, 80s, 80년대, 네온 드라이브, retrowave]
---
# Neon synthwave sunset (verified)
Rules: only magenta, cyan, yellow on a deep purple base; glow = HDR values (>1.0) + bloom threshold 1.0, so the dark mountains stay dark. Grid lines come from `fract` + `fwidth` (crisp at any distance) and scroll with `uTime`; fade with `exp(-dist*k)` so the horizon is clean. Sun stripes: horizontal slits whose thickness grows toward the sun bottom. For a car/drive game add the player on this floor and move the grid UV instead of objects.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>네온 석양</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#12002b}canvas{display:block}#t{position:fixed;left:0;right:0;top:7%;text-align:center;color:#fff;font:800 clamp(28px,6vw,64px) sans-serif;letter-spacing:.18em;text-shadow:0 0 12px #ff3cac,0 0 32px #ff3cac;pointer-events:none}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="t">네온 드라이브</div>
<script type="module">
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 400);
camera.position.set(0, 2.2, 8);
camera.lookAt(0, 2.8, -40);

// sky dome: purple -> magenta -> orange at the horizon, with a striped sun disc
const sky = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false,
  vertexShader: `varying vec3 vDir; void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `varying vec3 vDir;
    void main() {
      float h = clamp(vDir.y, 0.0, 1.0);
      vec3 col = mix(vec3(1.0, 0.45, 0.2), vec3(0.9, 0.12, 0.55), smoothstep(0.0, 0.12, h));
      col = mix(col, vec3(0.2, 0.03, 0.4), smoothstep(0.1, 0.55, h));
      vec2 sp = vec2(vDir.x, vDir.y - 0.17) / 0.2;                       // sun centre slightly above the horizon
      float d = length(sp);
      float t = (0.17 - vDir.y) / 0.2;                                   // 0 at the sun centre, 1 at its bottom edge
      float cut = step(0.0, t) * step(fract(vDir.y * 70.0), t * 0.65);   // horizontal slits, thicker toward the bottom
      float sunMask = (1.0 - smoothstep(0.96, 1.0, d)) * (1.0 - cut);
      vec3 sunCol = mix(vec3(1.0, 0.15, 0.5), vec3(1.0, 0.85, 0.2), clamp(sp.y * 0.5 + 0.6, 0.0, 1.0)) * 1.4;
      col = mix(col, sunCol, sunMask * step(0.0, vDir.y + 0.02));
      gl_FragColor = vec4(col, 1.0);
      #include <colorspace_fragment>
    }`,
}));
scene.add(sky);

// moving neon grid floor: lines come from fract() of world coordinates, scroll with uTime
const floorMat = new THREE.ShaderMaterial({
  transparent: true,
  uniforms: { uTime: { value: 0 } },
  vertexShader: `varying vec2 vXZ; varying float vDist; void main() { vXZ = position.xy; vec4 mv = modelViewMatrix * vec4(position, 1.0); vDist = -mv.z; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `uniform float uTime; varying vec2 vXZ; varying float vDist;
    void main() {
      vec2 p = vec2(vXZ.x, vXZ.y + uTime * 6.0) / 2.0;
      vec2 g = abs(fract(p - 0.5) - 0.5) / fwidth(p);
      float line = 1.0 - min(min(g.x, g.y), 1.0);
      float fade = exp(-vDist * 0.028);
      vec3 col = mix(vec3(0.06, 0.0, 0.16), vec3(0.1, 0.8, 1.0) * 1.3, line);
      gl_FragColor = vec4(col * fade, 1.0);
      #include <colorspace_fragment>
    }`,
});
const floor = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), floorMat);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// mountains: dark low-poly silhouettes with a glowing magenta edge (the edge is what sells the style)
const mtnGeo = new THREE.ConeGeometry(14, 14, 4, 1);
const mtnMat = new THREE.MeshBasicMaterial({ color: 0x14002e });
const edgeMat = new THREE.LineBasicMaterial({ color: new THREE.Color(1.0, 0.2, 0.7).multiplyScalar(1.6) });
const edges = new THREE.EdgesGeometry(mtnGeo);
for (let i = 0; i < 9; i++) {
  const side = i % 2 ? 1 : -1, k = Math.floor(i / 2);
  const m = new THREE.Group();
  m.add(new THREE.Mesh(mtnGeo, mtnMat), new THREE.LineSegments(edges, edgeMat));
  m.position.set(side * (20 + k * 9 + (i % 3) * 4), 5 + (i % 3) * 1.5, -60 - k * 14);
  m.scale.set(1 + (i % 3) * 0.3, 0.8 + (i % 4) * 0.35, 1);
  m.rotation.y = i;
  scene.add(m);
}

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.7, 0.5, 1.0));
composer.addPass(new OutputPass());

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  floorMat.uniforms.uTime.value += dt;
  composer.render(dt);
});
window.__s = { renderer };
</script>
</body>
</html>
```
