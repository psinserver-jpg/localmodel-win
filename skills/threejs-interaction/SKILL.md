---
name: threejs-interaction
description: User interaction in three.js - OrbitControls settings, third-person WASD walker with follow camera, PointerLock first person with wall collision, Raycaster picking/hover/drag, touch joystick, HTML labels, lil-gui/HTML controls, resize. Use for any three.js mouse, keyboard, touch, click, drag, camera-control or UI request.
triggers: [orbitcontrols, orbit controls, 마우스, mouse, 클릭, click, 드래그, drag, 선택, select, picking, raycaster, 레이캐스트, hover, 호버, tooltip, 툴팁, wasd, 키보드, keyboard, 이동, 조작, 컨트롤, controls, pointerlock, pointer lock, 1인칭, first person, 3인칭, third person, 터치, touch, 조이스틱, joystick, lil-gui, gui, 슬라이더, slider, 버튼, button, css2drenderer, 라벨, 상호작용, interactive, interaction]
priority: 48
---
# three.js interaction (r160)

Setup/import map: `threejs-basics`. Games with rules and score: `threejs-game`.

## Choose the control scheme
| Request | Use |
|---|---|
| look at / inspect a model, product viewer | `OrbitControls` |
| walk a character around, see it from behind | third-person walker (reference `third-person-walker`) |
| walk inside a room/museum/maze | `PointerLockControls` + AABB collision (reference `first-person-room`) |
| click/hover/drag objects, tooltips | `Raycaster` (reference `pick-drag`) |
| sliders/colour/toggles | lil-gui via import map, or plain HTML inputs |

## Hard rules
1. ONE input layer: keyboard + pointer events produce a single movement vector; mouse and touch use **pointer events** (`pointerdown/move/up`), not separate mouse/touch handlers. `touch-action: none` on body/canvas so the page does not scroll or zoom.
2. Movement uses `dt`, is camera-relative on the ground plane (`camera.getWorldDirection(v); v.y = 0; v.normalize()`), diagonals normalised, speed eased with `damp` (never snap).
3. `keys` as a `Set` of `e.code` (`KeyW`, `ArrowUp`, `Space`); clear it on `window blur`; `preventDefault` for arrows/space.
4. Rotate toward the move direction with the SHORTEST angle (wrap the difference to -PI..PI) and damped: `a += d * (1 - Math.exp(-12 * dt))`.
5. Collision: keep AABBs `{minX,maxX,minZ,maxZ}`; test X and Z axes separately so the player slides along walls; player radius 0.35-0.4.
6. Follow camera: `camPos = damp(camPos, player + offset)`, then `camera.lookAt(player + (0, 1.2, 0))`. Do not use OrbitControls at the same time.
7. When dragging an object, set `controls.enabled = false` and re-enable on `pointerup`/`pointercancel`.
8. Always handle `resize` (aspect, `updateProjectionMatrix`, `setSize`, label renderer too). Show the controls on screen in the user's language.
9. PointerLock needs a user click (`controls.lock()`); show a "click to start" overlay and listen for `lock`/`unlock`.

## OrbitControls (verified settings)
```js
// fragment
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;  controls.dampingFactor = 0.08;   // call controls.update() EVERY frame
controls.minDistance = 4;  controls.maxDistance = 25;
controls.maxPolarAngle = Math.PI * 0.49;                          // cannot go below the floor
controls.target.set(0, 1, 0);                                     // what it orbits around
controls.autoRotate = true;  controls.autoRotateSpeed = 1.5;      // optional showcase spin
controls.enablePan = false;                                       // optional
```

## Picking in 12 lines (verified: hover, select, drag all worked)
```js
// fragment
const raycaster = new THREE.Raycaster(), ndc = new THREE.Vector2();
function pick(e) {
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);   // Y is flipped
  raycaster.setFromCamera(ndc, camera);
  const hit = raycaster.intersectObjects(items, true)[0];          // `items` = ONLY pickable roots (not the floor); true = children
  if (!hit) return null;
  let o = hit.object; while (o.parent && !items.includes(o)) o = o.parent;   // loaded models: climb to the root
  return { object: o, point: hit.point };
}
// hover: emissive 0x333333 on the hovered mesh, reset the previous one; cursor = 'pointer'
// drag: Plane(new Vector3(0,1,0), -object.position.y); raycaster.ray.intersectPlane(plane, point); object.position.x = point.x ...
// tooltip: absolutely positioned div at (clientX + 14, clientY + 14)
// label above an object: CSS2DObject(div) added as a child; labelRenderer.render(scene, camera) after renderer.render
```
Full page (hover highlight, click select with label, drag on a plane, lil-gui sliders): `skill("threejs-interaction", "pick-drag")`.
Third-person walker with joystick: `skill("threejs-interaction", "third-person-walker")`. First-person room: `skill("threejs-interaction", "first-person-room")`. COPY them and change theme.

## lil-gui
Import map entry `"lil-gui": "https://cdn.jsdelivr.net/npm/lil-gui@0.19/+esm"`, then `import GUI from 'lil-gui'; const gui = new GUI({ title: '설정' }); gui.add(params, 'speed', 0, 10, 0.1).name('속도'); gui.addColor(params, 'color').onChange(v => mesh.material.color.set(v));`. Plain HTML buttons/sliders are fine too: put them in a `position:fixed` bar; `input` event for sliders.

## Pitfalls
Nothing is hit (`items` empty, floor included, wrong NDC, canvas not at 0,0 - use `getBoundingClientRect`) - clicking the sky selects the floor (exclude it) - orbit and drag fight (disable controls) - character turns the long way (angle wrap) - camera jitter (follow camera updated before the player moved, or two cameras logic) - stuck keys after alt-tab (clear on blur) - walking through walls (no collision, or only testing the combined move) - diagonal speed boost - mobile has no keyboard (joystick: pointer events on a div, `setPointerCapture` in try/catch) - `PointerLockControls` does nothing on touch devices (offer OrbitControls or drag-to-look there) - HUD blocks the canvas (`pointer-events:none` on the overlay).
