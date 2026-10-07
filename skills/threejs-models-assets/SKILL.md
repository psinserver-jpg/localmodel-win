---
name: threejs-models-assets
description: Get 3D content into three.js - primitive-built models via factory functions (tree, house, car, robot, rock, mountain), GLTFLoader with fallback, fitting and animating loaded models, InstancedMesh forests, merged geometry, procedural terrain and water. Use for any three.js model, GLTF/GLB, character, asset, terrain or "build a scene with objects" request.
triggers: [gltf, glb, gltfloader, 3d model, 3d 모델, model, 모델, 모델 불러, 불러와, load model, asset, assets, 에셋, character, 캐릭터, robot, 로봇, tree, 나무, house, 집, car, 자동차, terrain, 지형, 산, mountain, water, 물, village, 마을, instancedmesh, texture, 텍스처, textureloader, draco, bufferGeometryutils, low poly, 로우폴리, 애니메이션 재생, clip, 장면 만들어, 도시, 숲, forest]
priority: 52
---
# three.js models and assets (r160)

Setup/import map: `threejs-basics`. Lights/materials: `threejs-materials-lighting`.

## Decision: primitives first
1. DEFAULT = build from primitives (Box/Cylinder/Cone/Sphere/Dodecahedron, `flatShading: true`, 2-4 colours). Always works offline on file://, no CORS, no loading screen, looks consistent.
2. Use a downloaded model ONLY if the user asks for a real model/GLB/GLTF or a specific creature. Then ALWAYS add `try/catch`-style error callback with a primitive fallback (the page must never be empty).
3. `file://` can load GLB from `https://` CDNs but NOT from local relative files (CORS). For local files tell the user to run `python3 -m http.server`.
4. Never invent a model URL. Verified free models (three.js r160 examples), base `https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/models/gltf/`: `RobotExpressive/RobotExpressive.glb` (14 clips: Idle, Walking, Running, Dance, Jump, Wave, Yes, No, Punch, ThumbsUp, Sitting, Standing, Death, WalkJump), `Soldier.glb`, `Xbot.glb`, `Horse.glb`, `Flamingo.glb`, `Parrot.glb`, `LittlestTokyo.glb`, `DamagedHelmet/glTF/DamagedHelmet.gltf`.

## Factory functions (the pattern for every object)
- `function makeTree(scale = 1) { const g = new THREE.Group(); ...; return g; }` - origin at the FEET (y=0 ground), +Z = front, units = metres.
- Shared materials created once (`const M = {...}`), geometry per call is fine for <200 objects; beyond that use InstancedMesh.
- Limbs/doors/wheels: put a pivot `Group` at the joint, add the mesh offset inside it, rotate the pivot (`legL.rotation.x = Math.sin(t*4)*0.7`). Rotating a mesh directly spins it around its centre.
- Set `castShadow`/`receiveShadow` in one helper `part(geo, mat, x, y, z)`.
- Human-ish proportions: torso 1 m, head 0.5 m, legs 1 m. House 3x2x3 + roof `ConeGeometry(r, 1.4, 4)` rotated 45 deg. Rock = `DodecahedronGeometry` squashed in y.
Full tested set (tree, house, car, robot with pivots, cactus, rock, mountain) + village scene with sky/fog/shadows: `skill("threejs-models-assets", "primitives-village")`.

## Load a GLTF safely (verified with RobotExpressive.glb)
```js
// fragment
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const loader = new GLTFLoader(manager);                 // manager = new THREE.LoadingManager() for a progress bar
loader.load(URL, (gltf) => {
  const model = gltf.scene;
  model.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  fitModel(model, 2);                                    // see reference: scale to height, stand on y=0, centre
  scene.add(model);
  mixer = new THREE.AnimationMixer(model);
  gltf.animations.forEach((clip) => { actions[clip.name] = mixer.clipAction(clip); });
  actions['Idle'].play();                                // loop: mixer.update(dt) every frame
}, undefined, (err) => { console.warn('load failed', err); scene.add(fallbackModel()); });
```
- Size is unknown: ALWAYS fit with `Box3`. **Rigged/skinned models: `Box3.setFromObject` can be 50x too big (the robot measured 149 m tall) - measure bone world positions instead** (`measure()` in the reference).
- Clip names differ per model: list `gltf.animations.map(c => c.name)`, build buttons from them, do not hard-code unless the model is known. One-shot clips: `setLoop(THREE.LoopOnce, 1); clampWhenFinished = true;` and return to Idle on the mixer `'finished'` event. Switch: `next.reset().fadeIn(0.4).play(); current.fadeOut(0.4)`.
- Wait for the load before using the model (`manager.onLoad`) - never access `model` at top level.
- Compressed (Draco) files need `DRACOLoader` + `setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/libs/draco/')` and `loader.setDRACOLoader(d)`. KTX2/Meshopt are rare - avoid.
- Materials are already PBR: add lights + `RoomEnvironment` for metals.
Complete page with clip buttons, progress bar, fallback: `skill("threejs-models-assets", "gltf-viewer")`.

## Many objects and big worlds
- Forest/crowd/bricks: `InstancedMesh(geo, mat, N)`, `setMatrixAt(i, matrix)` with `matrix.compose(position, quaternion, scale)`, `mesh.count = placed`, `instanceMatrix.needsUpdate = true`. Per-instance colour: `setColorAt(i, color)`.
- Static decoration: `BufferGeometryUtils.mergeGeometries([g1, g2])` after `g.translate(x,y,z)` (all geometries need the same attributes) = one draw call.
- Terrain: `PlaneGeometry(size, size, 128, 128)`, `geo.rotateX(-Math.PI/2)` FIRST, then set each vertex Y from a hand-written noise `heightAt(x,z)`, vertex colours by height, `computeVertexNormals()`. Place trees with the same `heightAt`. Water = transparent plane at sea level. Tested page: `skill("threejs-models-assets", "terrain-instancing")`.
- Textures: `new THREE.TextureLoader().load(url)`; colour maps `texture.colorSpace = THREE.SRGBColorSpace`; tiling `wrapS = wrapT = THREE.RepeatWrapping; repeat.set(8, 8)`. Prefer vertex colours/solid colours: no files, no CORS.

## Pitfalls
Model invisible or tiny (not fitted - skinned bbox) - model black (no lights) - white/grey ghost (textures failed, check console) - sliding feet or T-pose (no `mixer.update(dt)`, no `.play()`) - CORS error on file:// (local file) - code runs before load - pivot confusion (limb rotates around its middle) - terrain flat shaded wrong (no `computeVertexNormals`) - terrain rotated wrong (rotate geometry before reading positions) - 5000 separate meshes (use InstancedMesh) - a model URL you invented (404).
