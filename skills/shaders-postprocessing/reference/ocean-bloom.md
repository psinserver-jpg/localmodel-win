---
name: ocean-bloom
description: Complete working page: displaced gradient ocean ShaderMaterial with fresnel and foam, glowing HDR sphere, EffectComposer with RenderPass, UnrealBloomPass and OutputPass.
triggers: [ocean shader, 바다 셰이더, wave shader, 물결, 파도, water shader, bloom example, 블룸 예제, effectcomposer example, glowing sphere, 물 셰이더, 바다]
---
# Shader ocean + bloom (verified, zero console errors)
Vertex shader displaces `position.z`, derives the normal from finite differences (so lighting/fresnel follow the waves), the mesh is rotated flat afterwards. The sun is a `MeshBasicMaterial` with colour multiplied above 1.0 so only it blooms (threshold 1.0). Change `uDeep/uShallow` for lakes, lava (`0x300000`/`0xff5a00`) or toxic goo.

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>셰이더 바다</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#050816}canvas{display:block}#hud{position:fixed;left:16px;top:12px;color:#cfe8ff;font:14px sans-serif}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head>
<body>
<div id="hud">셰이더 바다 + 블룸 (드래그로 회전)</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
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
scene.background = new THREE.Color(0x050816);
const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 5, 14);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.2, 0);
controls.enableDamping = true;

// wavy gradient ocean: displace in the vertex shader, colour by height + fresnel in the fragment shader
const ocean = new THREE.Mesh(
  new THREE.PlaneGeometry(60, 60, 200, 200),
  new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uDeep: { value: new THREE.Color(0x021030) }, uShallow: { value: new THREE.Color(0x0f6f8f) } },
    vertexShader: /* glsl */`
      uniform float uTime;
      varying float vH;
      varying vec3 vNormal;
      varying vec3 vView;
      float wave(vec2 p) {
        return sin(p.x * 0.5 + uTime) * 0.45 + sin(p.y * 0.8 - uTime * 1.3) * 0.3 + sin((p.x + p.y) * 0.35 + uTime * 0.7) * 0.35;
      }
      void main() {
        vec3 p = position;                       // plane is XY, z = height (mesh is rotated flat later)
        float e = 0.1;
        float h = wave(p.xy);
        vec3 n = normalize(vec3(h - wave(p.xy + vec2(e, 0.0)), h - wave(p.xy + vec2(0.0, e)), e));
        p.z += h;
        vH = h;
        vNormal = normalMatrix * n;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vView = -mv.xyz;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uDeep; uniform vec3 uShallow;
      varying float vH; varying vec3 vNormal; varying vec3 vView;
      void main() {
        vec3 n = normalize(vNormal);
        vec3 v = normalize(vView);
        float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);        // fresnel: grazing angles reflect the sky
        vec3 col = mix(uDeep, uShallow, smoothstep(-0.9, 1.0, vH));
        col = mix(col, vec3(0.9, 0.45, 0.25) * 0.5, fres * 0.6);   // sky tint from the glowing sun side
        col += vec3(0.5, 0.7, 0.8) * smoothstep(0.85, 1.05, vH) * 0.25;  // foam on crests
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
  })
);
ocean.rotation.x = -Math.PI / 2;
scene.add(ocean);

// glowing sphere: emissive colour above 1.0 is what bloom picks up
const orb = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.0, 0.55, 0.2).multiplyScalar(3) }));
orb.position.y = 2;
scene.add(orb);

// postprocessing order: render -> bloom -> output (tone mapping + sRGB happen in OutputPass)
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.8, 0.5, 1.0);
composer.addPass(bloom);
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
  ocean.material.uniforms.uTime.value += dt;
  orb.position.y = 2 + Math.sin(ocean.material.uniforms.uTime.value * 1.5) * 0.4;
  controls.update();
  composer.render(dt);
});
window.__t = { ocean, orb, bloom, composer, renderer };
</script>
</body>
</html>
```
