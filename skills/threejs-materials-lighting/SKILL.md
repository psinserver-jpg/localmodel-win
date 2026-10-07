---
name: threejs-materials-lighting
description: Make three.js scenes look good - correct r160 light intensities, shadows that actually appear, PBR materials (roughness/metalness), environment reflections, tone mapping, fog, procedural textures, toon and glass. Use for any lighting, shadow, material, texture, reflection or "make it look nicer" three.js request.
triggers: [material, materials, 재질, 질감, light, lights, lighting, 조명, 빛, shadow, shadows, 그림자, pbr, texture, textures, 텍스처, environment map, envmap, hdri, reflection, 반사, tone mapping, fog, 안개, standardmaterial, meshstandardmaterial, physicalmaterial, toon, 툰, roughness, metalness, emissive, 발광, glass, 유리, metal, 금속, directionallight, pointlight, spotlight, 라이트]
priority: 52
---
# three.js materials and lighting (r160)

## Light rules (physical units since r155 - old tutorials are wrong)
- `DirectionalLight` 1.5-3 (sun), `HemisphereLight`/`AmbientLight` 0.3-1.2 (fill), `PointLight` 30-300 and `SpotLight` 100-800 (they fade with distance, `decay = 2`). If a point light looks dead, multiply its intensity by 10.
- Start every scene with: Hemisphere (sky colour, ground colour) + one Directional with shadows. Add 1-2 coloured point lights for mood. Never rely on AmbientLight alone (flat look).
- Warm key + cool fill: key `0xfff1d6`, fill/sky `0x9ec9ff`.

## Shadows - the 5 things that must all be true
1. `renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;`
2. `light.castShadow = true` (only Directional/Point/Spot).
3. Every object that should cast: `mesh.castShadow = true`; the ground: `mesh.receiveShadow = true`.
4. **The shadow camera must cover the scene** (the usual reason shadows are cut off or missing): `Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15, near: 1, far: 50 }); sun.shadow.camera.updateProjectionMatrix();`
5. Quality: `sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.02;` (acne -> raise normalBias; floating shadow -> lower it).
Keep the frustum as small as the play area: smaller = sharper.

## Pick the material
| Need | Material |
|---|---|
| default realistic | `MeshStandardMaterial({ color, roughness: 0.6, metalness: 0 })` |
| car paint / glass / gems | `MeshPhysicalMaterial({ clearcoat: 1, transmission: 1, thickness: 0.5, ior: 1.5, roughness: 0.05 })` |
| cheap + matte (many objects, mobile) | `MeshLambertMaterial` |
| cartoon | `MeshToonMaterial({ color, gradientMap })` |
| UI-like, sky, glow sprites, no lighting | `MeshBasicMaterial` |
| quick sculpt look | `MeshMatcapMaterial` |
Roughness 0.1 = mirror-like, 1 = chalk. Metalness is 0 (plastic, wood, skin, stone) or 1 (metal) - avoid 0.5. `flatShading: true` gives the low-poly look. `emissive` + `emissiveIntensity` makes things glow (pair with bloom, see `shaders-postprocessing`). Transparent glow: `transparent: true, opacity: .6, depthWrite: false`.

## Colour management (why things look washed out)
`renderer.outputColorSpace = THREE.SRGBColorSpace` (default in r160). Hex colours are already sRGB. For loaded colour textures set `texture.colorSpace = THREE.SRGBColorSpace`; normal/roughness/ao maps stay linear (default). Never set colours with `0xffffff` everywhere - pure white blows out; use `0xf2efe8`.

## Reflections need an environment (metals look black without)
```js
// fragment
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;   // no download needed
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
```
Lower `scene.environmentIntensity = 0.6` (r163+) or use `material.envMapIntensity` if it is too bright.

## Verified lighting block (drop into the basics template)
```js
// fragment
scene.background = new THREE.Color(0xbfe3ff);
scene.fog = new THREE.Fog(0xbfe3ff, 25, 90);              // same colour as the background = natural depth
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x7a6a4f, 1.0));
const sun = new THREE.DirectionalLight(0xfff1d6, 2.4);
sun.position.set(8, 14, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15, near: 1, far: 50 });
sun.shadow.bias = -0.0005;
sun.shadow.normalBias = 0.02;
scene.add(sun);
```

## Problems -> fixes
Object black: no light / `MeshBasicMaterial` test / env missing for metal. Too bright & white: lower intensities, ACES tone mapping, avoid pure white. Flat grey look: add hemisphere light, vary roughness, add fog, coloured ground. Banding in gradients/fog: add subtle noise or lower fog density. Transparent objects flicker: `depthWrite: false`, set `renderOrder`. Texture stretched: `texture.wrapS = texture.wrapT = THREE.RepeatWrapping; texture.repeat.set(8, 8)`. More recipes (toon, glass, neon, studio, golden hour, night, procedural textures): `skill("threejs-materials-lighting", "recipes")`.
