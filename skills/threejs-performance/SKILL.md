---
name: threejs-performance
description: Make three.js scenes run at a smooth 60 fps on phones and weak PCs - pixel ratio, shadows, draw calls, InstancedMesh, reuse and dispose, pooling, no per-frame allocation, culling, LOD, fog, on-demand rendering, FPS overlay and leak hunting. Use for any three.js lag, slow, FPS, optimization or memory-leak request.
triggers: [three.js performance, three.js optimization, three.js optimize, 3d performance, 3d optimization, webgl performance, instancedmesh, instanced mesh, draw calls, draw call, renderer.info, dispose, memory leak, object pooling, lod, level of detail, frustum culling, mergegeometries, 60fps, 60 fps, fps counter, three.js 최적화, three.js 성능, 3d 최적화, 3d 성능, 3d 렉, 3d 버벅, 렉 걸려, 버벅거, 프레임 떨어, 프레임 드랍, 드로우콜, 인스턴싱, 메모리 누수, 모바일 성능, 모바일 3d, 가볍게 만들, 오브젝트 풀]
priority: 44
---
# three.js performance (r160)

## Budget (aim for phones: 1 GPU, small battery)
Draw calls < 100 (ideal < 50), triangles < 300k, shadow-casting lights 1, lights < 4, textures <= 2048px, pixel ratio <= 1.5-2. Measure first: `renderer.info.render.calls / .triangles`, `renderer.info.memory.geometries / .textures`. Add the overlay from `skill("threejs-performance", "instanced-overlay")` (verified).

## Fixes in order of impact
1. **Draw calls**: 1000 similar things = one `InstancedMesh(geo, mat, count)`; set `mesh.setMatrixAt(i, m)` and `mesh.instanceMatrix.needsUpdate = true` (+ `setUsage(THREE.DynamicDrawUsage)` if rewritten every frame); per-instance colour via `setColorAt`. Static scenery: merge with `mergeGeometries` from `three/addons/utils/BufferGeometryUtils.js` (same material). One material per kind, never per object.
2. **Pixel ratio**: `renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5))` (phones 1-1.5). It scales fragment cost by its square.
3. **Shadows**: one `DirectionalLight` shadow, `mapSize` 1024 (2048 desktop), tight frustum (`left/right/top/bottom` just over the play area). Static scene? render once: `renderer.shadowMap.autoUpdate = false; renderer.shadowMap.needsUpdate = true;`. Few `castShadow` meshes. No shadow on tiny props.
4. **Cheap materials**: `MeshLambertMaterial` / `MeshBasicMaterial` for many objects; `MeshPhysicalMaterial` (transmission, clearcoat) only on 1-3 hero objects. Avoid big transparent overlaps (overdraw). `antialias: false` + pixelRatio 2 is often better than antialias at 1; on mobile keep it false.
5. **Geometry**: segments only where needed (`SphereGeometry(1, 24, 16)` not 64x64). Share ONE geometry/material across meshes (`const geo = new ...` outside functions and loops).
6. **Never allocate per frame**: no `new Vector3/Color/Matrix4/Quaternion` in `update()`; create module-level temps and use `.set/.copy/.compose`. No array `.map/.filter/spread` in hot loops. No `new Mesh` per bullet/particle: pool.
7. **Culling & distance**: frustum culling is on by default (instanced: `mesh.computeBoundingSphere()` after moving instances far from origin). `scene.fog` + camera `far` small lets you skip far objects. `THREE.LOD`: `lod.addLevel(highMesh, 0); lod.addLevel(lowMesh, 40); scene.add(lod)`.
8. **Textures**: power-of-two <= 2048 (1024 for mobile), `texture.anisotropy = 4`, `generateMipmaps` stay true, prefer one atlas; `texture.colorSpace = THREE.SRGBColorSpace` for colour maps. KTX2/Basis compression is the real fix for big texture sets.
9. **Render only when needed** (viewers, configurators): `renderer.setAnimationLoop(null)` and call `renderer.render` on controls `change` events, or flag `needsRender`.
10. **Postprocessing off on phones** (`/Mobi|Android/i.test(navigator.userAgent)` -> plain `renderer.render`). Bloom/SSAO = full-screen passes.

## Pooling + dispose (copy)
```js
// fragment
const pool = [];
function getBullet() {
  let b = pool.pop();
  if (!b) { b = new THREE.Mesh(bulletGeo, bulletMat); scene.add(b); }   // shared geo/mat created once
  b.visible = true;
  return b;
}
function freeBullet(b) { b.visible = false; pool.push(b); }
// real removal of something that owns unique resources:
function disposeObject(root) {
  root.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
    for (const m of mats) { for (const k in m) if (m[k] && m[k].isTexture) m[k].dispose(); m.dispose(); }
  });
  root.removeFromParent();
}
```
Dispose also: `renderTarget.dispose()`, `composer` passes on teardown, `texture.dispose()` for canvas textures you recreate. `scene.remove(mesh)` alone leaks GPU memory.

## Pause when hidden + clamp
```js
// fragment
let running = true;
document.addEventListener('visibilitychange', () => { running = !document.hidden; clock.getDelta(); });
// in loop: const dt = Math.min(clock.getDelta(), 0.05); if (!running) return;
```
`renderer.setAnimationLoop(fn)` is preferred over manual `requestAnimationFrame` (handles XR, one loop, `setAnimationLoop(null)` stops it). rAF already pauses in hidden tabs; the clamp prevents the jump on return.

## Leak hunting
Log `renderer.info.memory` every few seconds: geometries/textures that only grow while you spawn and remove things = missing `dispose()` or `new` per spawn. `renderer.info.render.calls` growing = objects never removed from the scene.

## Pitfalls
FPS on desktop headless/software GL is NOT representative: judge by draw calls and triangles. Moving instances every frame in JS: 5000 is fine, 100k needs a vertex shader. `Raycaster` against thousands of meshes per frame is slow: ray only against a short list, or do it on pointer events.
Verified example: `skill("threejs-performance", "instanced-overlay")`.
