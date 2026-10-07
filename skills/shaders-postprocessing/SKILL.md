---
name: shaders-postprocessing
description: Write custom GLSL shaders and postprocessing in three.js r160 - ShaderMaterial, waves, fresnel/hologram, dissolve, toon outline, sky and star shaders, onBeforeCompile, EffectComposer with bloom, vignette and custom passes. Use for any shader, GLSL, glow/bloom, post-processing or special-effect request.
triggers: [shader, shaders, glsl, shadermaterial, rawshadermaterial, fragment shader, vertex shader, uniforms, onbeforecompile, postprocessing, post-processing, post processing, effectcomposer, bloom, unrealbloompass, fresnel, hologram, dissolve, vignette, chromatic aberration, 셰이더, 쉐이더, 쉐이더로, 글로우 효과, 블룸, 후처리, 포스트프로세싱, 프레넬, 홀로그램, 디졸브, 물결 효과, 파도 효과, 외곽선 효과, 비네트, 픽셀화 효과, 네온 글로우]
priority: 48
---
# Shaders and postprocessing (three.js r160)

## Hard rules
1. `ShaderMaterial` auto-declares `position, normal, uv`, `modelMatrix, modelViewMatrix, viewMatrix, projectionMatrix, normalMatrix, cameraPosition` and adds `precision`. `RawShaderMaterial` declares NOTHING (avoid it). Never redeclare those names.
2. Uniforms are objects: `uniforms: { uTime: { value: 0 } }`. Update `mat.uniforms.uTime.value += dt` every frame (dt clamped 0.05). Colors: `{ value: new THREE.Color(0xff8800) }` -> `uniform vec3`.
3. For correct sRGB output end the fragment shader with `#include <colorspace_fragment>` **on its own line** (a `#include` inside a one-line template string with code after it = "invalid character" compile error). With EffectComposer end with `OutputPass` instead (it does tone mapping + sRGB; shader colour is then linear and `#include` is harmless).
4. Shader errors appear ONLY in the console (`THREE.WebGLProgram: Shader Error`): read the line number, it is relative to the generated header. Black mesh = compile error or alpha 0.
5. Glow/ghost layers: `transparent: true, depthWrite: false, blending: THREE.AdditiveBlending`. Plane/knot seen from the back: `side: THREE.DoubleSide`.
6. A plane built with PlaneGeometry is XY (z = out of the plane). Displace `position.z` and rotate the MESH (`rotation.x = -Math.PI/2`), or call `geo.rotateX(-Math.PI/2)` first and displace `y`.
7. Postprocessing order is fixed: `RenderPass` -> effects (`UnrealBloomPass`, `ShaderPass`) -> `OutputPass` LAST. Render with `composer.render(dt)` instead of `renderer.render`, and on resize call `renderer.setSize` AND `composer.setSize`.
8. Bloom only glows pixels brighter than its threshold. Make glowing things HDR: `new THREE.Color(1, .55, .2).multiplyScalar(3)` on a MeshBasicMaterial, or emissive with `emissiveIntensity` 2-4. Keep threshold ~1.0 so the scene does not wash out; strength 0.5-1.0.
9. Skip postprocessing on phones/low-end (cost = extra full-screen passes); use emissive materials + sprites instead.

## Skeleton
```js
// fragment
const mat = new THREE.ShaderMaterial({
  uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(0x27d8ff) } },
  vertexShader: `
    varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vView = normalize(-mv.xyz);
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `
    uniform float uTime; uniform vec3 uColor;
    varying vec2 vUv; varying vec3 vNormal; varying vec3 vView;
    void main() {
      float fres = pow(1.0 - max(dot(normalize(vNormal), vView), 0.0), 3.0);   // rim glow
      gl_FragColor = vec4(uColor * (0.3 + fres * 2.0), 1.0);
      #include <colorspace_fragment>
    }`,
});
```

## Effect cheat sheet (all verified in `skill("shaders-postprocessing", "effects-library")`)
- Vertex wave: `p.z += sin(p.x*0.5+uTime)*0.4`; normal from finite differences (see `ocean-bloom`).
- Gradient by height: `mix(uDeep, uShallow, smoothstep(-1.0, 1.0, vH))`.
- Fresnel: `pow(1.0 - abs(dot(N, V)), 2.5)`; hologram = fresnel + `sin(worldY*40 - uTime*4)` scanlines + additive blending (`hologram`).
- Dissolve: `if (noise < uProgress) discard;` plus a bright edge `smoothstep(p, p+0.06, noise)`.
- Toon outline: second mesh, same geometry, `side: BackSide`, `position + normal * 0.04`, flat dark colour.
- Keep PBR and add a custom bit: `material.onBeforeCompile = (s) => { s.uniforms.uTime = shared; s.fragmentShader = s.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\n...') }`.
- Sky: BackSide sphere, `depthWrite: false`, colour from `normalize(position).y`. Stars: `Points` + ShaderMaterial, `gl_PointSize`, discard outside radius 0.5.
- GLSL helpers (hash21, vnoise, fbm) and a vignette/chromatic/pixelate `ShaderPass`: `effects-library`.

## Minimal composer (copy exactly)
```js
// fragment
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.8, 0.5, 1.0)); // strength, radius, threshold
composer.addPass(new OutputPass());
// loop: composer.render(dt);   resize: composer.setSize(innerWidth, innerHeight);
```

## Pitfalls
- Everything bloomed looks foggy: lower strength, raise threshold, make only the glowing objects HDR.
- `fwidth()` works in WebGL2 (r160 default) without extensions. `discard` costs overdraw; do not use on huge areas.
- Loops need constant bounds (`for (int i = 0; i < 5; i++)`). `int`/`float` never mix: write `1.0`, not `1`.
- Many uniforms updated per object -> share ONE uniform object between materials (`u.uTime = sharedTime`).
- Custom look on an `InstancedMesh`: patch a standard material with `onBeforeCompile` (instancing keeps working); a raw ShaderMaterial needs manual `instanceMatrix` handling.
Deep examples: `skill("shaders-postprocessing", "ocean-bloom")`, `"hologram"`, `"effects-library"`.
