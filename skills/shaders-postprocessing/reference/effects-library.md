---
name: effects-library
description: One verified page with GLSL noise helpers (hash, value noise, fbm), noise dissolve with glowing edge, toon material with inverted-hull outline, onBeforeCompile patch of MeshStandardMaterial, shader starfield Points, gradient sky dome, and a custom ShaderPass (chromatic aberration, vignette, pixelate).
triggers: [glsl noise, fbm, 노이즈, dissolve, 디졸브, outline, 외곽선, toon outline, onbeforecompile, starfield shader, 별, sky shader, 하늘 셰이더, vignette, 비네트, chromatic aberration, pixelate, 픽셀화, shaderpass, custom pass, 커스텀 패스]
---
# Shader effects library (one page, all verified)
Left to right: dissolve (progress animates), toon + outline, striped PBR via `onBeforeCompile` (still lit and shadowed), starfield + sky dome behind. The composer ends with a custom `ShaderPass` then `OutputPass`. Set `fx.uniforms.uPixels.value = 120` for a pixel-art look, `uAberration` 0.006 for glitch, `uVignette` 0 to turn off.
Notes: `#include <colorspace_fragment>` must be on its own line; `ShaderPass` fragment writes plain `gl_FragColor` (OutputPass converts); star `uPx` uniform keeps point size right on retina.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>셰이더 모음</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#000}canvas{display:block}#hud{position:fixed;left:16px;top:12px;color:#fff;font:14px sans-serif}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">왼쪽부터: 디졸브 / 툰+외곽선 / 패치된 PBR / 별 + 하늘</div>
<script type="module">
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 500);
camera.position.set(0, 1.5, 11);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x445566, 1.2));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.5);
sun.position.set(4, 6, 5);
scene.add(sun);

// shared GLSL helpers (hash / value noise / fbm) - paste into any fragment shader
const NOISE = /* glsl */`
float hash21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash21(i), hash21(i + vec2(1, 0)), f.x), mix(hash21(i + vec2(0, 1)), hash21(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p *= 2.0; a *= 0.5; } return s; }
`;

// 1) dissolve: discard where noise < threshold, glow on the burning edge
const dissolveMat = new THREE.ShaderMaterial({
  side: THREE.DoubleSide,
  uniforms: { uProgress: { value: 0 }, uColor: { value: new THREE.Color(0x3a7bd5) } },
  vertexShader: `varying vec3 vP; varying vec3 vN; void main() { vP = position; vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: NOISE + /* glsl */`
    uniform float uProgress; uniform vec3 uColor; varying vec3 vP; varying vec3 vN;
    void main() {
      float n = fbm(vP.xy * 2.5 + vP.z * 1.7);
      if (n < uProgress) discard;
      float edge = smoothstep(uProgress, uProgress + 0.06, n);
      vec3 lit = uColor * (0.35 + 0.65 * max(dot(vN, normalize(vec3(0.4, 0.8, 0.6))), 0.0));
      gl_FragColor = vec4(mix(vec3(3.0, 1.2, 0.3), lit, edge), 1.0);   // >1.0 so bloom would pick the edge up
      #include <colorspace_fragment>
    }`,
});
const dissolve = new THREE.Mesh(new THREE.IcosahedronGeometry(1.3, 4), dissolveMat);
dissolve.position.set(-4.5, 0, 0);
scene.add(dissolve);

// 2) toon + inverted-hull outline: second mesh, BackSide, pushed out along normals
const toonMesh = new THREE.Mesh(new THREE.TorusKnotGeometry(0.9, 0.32, 128, 24), new THREE.MeshToonMaterial({ color: 0xff8a65 }));
const outline = new THREE.Mesh(toonMesh.geometry, new THREE.ShaderMaterial({
  side: THREE.BackSide,
  uniforms: { uWidth: { value: 0.04 } },
  vertexShader: `uniform float uWidth; void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position + normal * uWidth, 1.0); }`,
  fragmentShader: `void main() { gl_FragColor = vec4(0.07, 0.05, 0.1, 1.0); }`,
}));
const toon = new THREE.Group();
toon.add(toonMesh, outline);
toon.position.set(-1.5, 0, 0);
scene.add(toon);

// 3) onBeforeCompile: keep PBR lighting/shadows, add a custom effect (animated stripes in the diffuse colour)
const patchTime = { value: 0 };
const patched = new THREE.MeshStandardMaterial({ color: 0x8e44ad, roughness: 0.4 });
patched.onBeforeCompile = (shader) => {
  shader.uniforms.uTime = patchTime;
  shader.vertexShader = 'varying vec3 vObjPos;\n' + shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvObjPos = position;');
  shader.fragmentShader = 'uniform float uTime;\nvarying vec3 vObjPos;\n' + shader.fragmentShader.replace(
    '#include <color_fragment>',
    '#include <color_fragment>\ndiffuseColor.rgb = mix(diffuseColor.rgb, vec3(1.0, 0.85, 0.3), step(0.5, fract(vObjPos.y * 3.0 - uTime)));');
};
const patchedMesh = new THREE.Mesh(new THREE.SphereGeometry(1.2, 48, 32), patched);
patchedMesh.position.set(1.8, 0, 0);
scene.add(patchedMesh);

// 4) starfield (Points + ShaderMaterial, per-star size and twinkle) and a gradient sky dome
const N = 1500, pos = new Float32Array(N * 3), seed = new Float32Array(N);
for (let i = 0; i < N; i++) {
  const v = new THREE.Vector3().randomDirection().multiplyScalar(60 + Math.random() * 20);
  pos.set([v.x, Math.abs(v.y) * 0.8 + 3, v.z - 20], i * 3);
  seed[i] = Math.random();
}
const starGeo = new THREE.BufferGeometry();
starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
starGeo.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
const starMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uTime: { value: 0 }, uPx: { value: renderer.getPixelRatio() } },
  vertexShader: `uniform float uTime; uniform float uPx; attribute float aSeed; varying float vA;
    void main() { vA = 0.5 + 0.5 * sin(uTime * (1.0 + aSeed * 3.0) + aSeed * 40.0);
      vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = (1.5 + aSeed * 3.0) * uPx; gl_Position = projectionMatrix * mv; }`,
  fragmentShader: `varying float vA; void main() { float d = length(gl_PointCoord - 0.5); if (d > 0.5) discard; gl_FragColor = vec4(vec3(1.0, 0.95, 0.85), (1.0 - d * 2.0) * (0.4 + 0.6 * vA));
 #include <colorspace_fragment>
 }`,
});
scene.add(new THREE.Points(starGeo, starMat));
const sky = new THREE.Mesh(new THREE.SphereGeometry(200, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  vertexShader: `varying vec3 vDir; void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `varying vec3 vDir; void main() { float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 col = mix(vec3(0.95, 0.45, 0.35), vec3(0.04, 0.05, 0.2), pow(h, 0.6)); gl_FragColor = vec4(col, 1.0);
 #include <colorspace_fragment>
 }`,
}));
scene.add(sky);

// custom full-screen pass: vignette + chromatic aberration + optional pixelate
const FxShader = {
  uniforms: { tDiffuse: { value: null }, uAberration: { value: 0.003 }, uVignette: { value: 0.35 }, uPixels: { value: 0 }, uAspect: { value: 1 } },
  vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uAberration, uVignette, uPixels, uAspect; varying vec2 vUv;
    void main() {
      vec2 uv = vUv;
      if (uPixels > 0.0) uv = (floor(uv * vec2(uPixels * uAspect, uPixels)) + 0.5) / vec2(uPixels * uAspect, uPixels);
      vec2 dir = (uv - 0.5) * uAberration;
      vec3 c = vec3(texture2D(tDiffuse, uv + dir).r, texture2D(tDiffuse, uv).g, texture2D(tDiffuse, uv - dir).b);
      c *= 1.0 - uVignette * smoothstep(0.35, 0.9, length(vUv - 0.5) * 1.4);
      gl_FragColor = vec4(c, 1.0);
    }`,
};
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const fx = new ShaderPass(FxShader);
composer.addPass(fx);
composer.addPass(new OutputPass());

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
  fx.uniforms.uAspect.value = camera.aspect;
});
fx.uniforms.uAspect.value = camera.aspect;

const clock = new THREE.Clock();
let t = 0;
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  t += dt;
  dissolveMat.uniforms.uProgress.value = 0.25 + 0.5 * (0.5 + 0.5 * Math.sin(t * 0.8));
  patchTime.value = t;
  starMat.uniforms.uTime.value = t;
  dissolve.rotation.y += dt * 0.5;
  toon.rotation.y += dt * 0.7;
  patchedMesh.rotation.y += dt * 0.3;
  composer.render(dt);
});
window.__t = { renderer, composer, fx, scene };
</script>
</body>
</html>
```
