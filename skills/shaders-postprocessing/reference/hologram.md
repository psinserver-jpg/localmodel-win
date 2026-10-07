---
name: hologram
description: Complete working page: hologram ShaderMaterial with fresnel rim, moving scanlines and a sweeping band, additive blending, on a torus knot.
triggers: [hologram example, 홀로그램, fresnel example, scanline, 스캔라인, sci-fi shader, 사이버 효과, forcefield, 방어막, 에너지 실드, ghost, 유령]
---
# Hologram / fresnel shader (verified)
Rules that make it work: `transparent`, `depthWrite: false`, `AdditiveBlending`, `DoubleSide`, alpha from fresnel + scanlines. Scanlines use WORLD y (`modelMatrix * position`) so they stay horizontal when the object rotates. Force-field shield: same material on a sphere, lower `0.08` base alpha, add `uHit` pulse uniform.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>홀로그램</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#02060f}canvas{display:block}#hud{position:fixed;left:16px;top:12px;color:#7fe9ff;font:14px sans-serif}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">홀로그램 (프레넬 + 스캔라인)</div>
<script type="module">
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x02060f);
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 0.5, 7);

const holo = new THREE.ShaderMaterial({
  transparent: true,
  depthWrite: false,                    // glow layers must not write depth
  blending: THREE.AdditiveBlending,
  side: THREE.DoubleSide,
  uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(0x27d8ff) } },
  vertexShader: /* glsl */`
    varying vec3 vN; varying vec3 vV; varying vec3 vW;
    void main() {
      vec4 wp = modelMatrix * vec4(position, 1.0);
      vW = wp.xyz;
      vec4 mv = viewMatrix * wp;
      vN = normalize(normalMatrix * normal);
      vV = normalize(-mv.xyz);
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: /* glsl */`
    uniform float uTime; uniform vec3 uColor;
    varying vec3 vN; varying vec3 vV; varying vec3 vW;
    void main() {
      float fres = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.5);
      float scan = 0.5 + 0.5 * sin(vW.y * 40.0 - uTime * 4.0);       // moving scanlines
      float sweep = smoothstep(0.96, 1.0, sin(vW.y * 1.5 - uTime * 1.2));   // bright band
      float a = clamp(fres * 1.4 + scan * 0.25 + sweep * 0.6 + 0.08, 0.0, 1.0);
      gl_FragColor = vec4(uColor * (0.6 + fres * 1.5 + sweep), a);
      #include <colorspace_fragment>
    }`,
});
const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1.4, 0.45, 220, 32), holo);
knot.position.y = 0.6;
scene.add(knot);
const base = new THREE.Mesh(new THREE.CylinderGeometry(2, 2.3, 0.15, 48, 1, true), holo);
base.position.y = -1.9;
scene.add(base);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  holo.uniforms.uTime.value += dt;
  knot.rotation.y += dt * 0.6;
  knot.rotation.x += dt * 0.2;
  renderer.render(scene, camera);
});
window.__t = { renderer, holo };
</script>
</body>
</html>
```
