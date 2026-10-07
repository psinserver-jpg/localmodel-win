---
name: threejs-physics-collision
description: Physics and collision for three.js games - own gravity/AABB/swept checks for simple games, cannon-es for stacking, rolling and many bodies, plus Raycaster ground checks, Box3/Sphere tests and pickups. Use for any gravity, jump, collision, bounce, rigid body, physics engine or hit-detection request in 3D.
triggers: [physics, physics engine, collision, collisions, collision detection, cannon-es, cannon.js, rigid body, rigidbody, gravity, raycaster, raycast, aabb, hitbox, bounce, restitution, ragdoll, stacking, knock down, pickup, trigger zone, 물리, 물리엔진, 물리 엔진, 충돌, 충돌 감지, 충돌 처리, 중력, 점프 물리, 바운스, 튕기, 튕겨, 쌓기, 쌓이, 래그돌, 레이캐스트, 레이캐스팅, 히트박스, 당구, 무너뜨리, 낙하]
priority: 48
---
# three.js physics and collision (r160)

## RULE 1 - simple game? write your own physics (no library)
Platformers, runners, shooters, top-down: a few lines beat an engine (smaller, no tunnelling surprises). Per frame with `dt` clamped to 0.05:
```
vy -= G * dt;   y += vy * dt;   if (feetY <= groundY) { feetY = groundY; vy = 0; onGround = true }
```
Numbers (check them BEFORE placing obstacles): jump speed `v`, gravity `g` -> apex = `v*v/(2g)`, airtime = `2v/g`. g=30, v=12 -> apex 2.4 m, air 0.8 s; g=9.8, v=8 -> apex 3.3 m, air 1.6 s. **Every obstacle/step must be <= 70% of apex**, every gap <= `speed * airtime * 0.7`. Terminal velocity: clamp `vy >= -40`. Bounce: `vy = -vy * restitution` (0.3 soft, 0.8 rubber) and stop when `|vy| < 1`.
- Move ONE axis at a time (x then resolve, y then resolve); AABB overlap: `a.min < b.max && a.max > b.min` on every axis. **Use an epsilon (0.001)** or standing on a top face counts as side overlap and you get pushed sideways.
- No tunnelling: split the step so no substep moves more than 0.25 m (`n = ceil(speed*dt/0.25)`), or sweep with a Raycaster along the motion.
- Feel: coyote time 0.1 s (jump just after leaving a ledge), jump buffer 0.12 s, release early = short hop.
- Sphere-sphere: `a.distanceTo(b) < ra + rb`. Sphere-box: `box.clampPoint(c, tmp).distanceTo(c) < r`. Use `THREE.Box3().setFromObject(mesh)` once for static things (not per frame).
- Full verified character: `skill("threejs-physics-collision", "platformer-custom")`.

## RULE 2 - stacking, rolling, many bodies, tumbling? use cannon-es
Import map entry: `"cannon-es": "https://cdn.jsdelivr.net/npm/cannon-es@0.20.0/dist/cannon-es.js"`, then `import * as CANNON from 'cannon-es'`.
```js
// fragment
const world = new CANNON.World({ gravity: new CANNON.Vec3(0, -9.82, 0) });
world.allowSleep = true;                                       // resting bodies cost nothing
const mat = new CANNON.Material('default');
world.addContactMaterial(new CANNON.ContactMaterial(mat, mat, { friction: 0.4, restitution: 0.35 }));
const ground = new CANNON.Body({ mass: 0, shape: new CANNON.Plane(), material: mat });   // mass 0 = static
ground.quaternion.setFromEuler(-Math.PI / 2, 0, 0);            // Plane faces +Z by default: rotate to face +Y
world.addBody(ground);
const body = new CANNON.Body({ mass: 1, shape: new CANNON.Box(new CANNON.Vec3(0.5, 0.5, 0.5)), material: mat, position: new CANNON.Vec3(0, 5, 0) });
world.addBody(body);
// every frame:
world.step(1 / 60, dt, 3);                                     // fixed step, up to 3 catch-up substeps
mesh.position.copy(body.position);
mesh.quaternion.copy(body.quaternion);
```
- **Box takes HALF extents** (mesh `BoxGeometry(1,1,1)` -> `Vec3(0.5,0.5,0.5)`); `Sphere(radius)`; cylinders/complex shapes: approximate with Box/Sphere compounds (`body.addShape(shape, offset)`).
- Sync direction: dynamic bodies drive meshes. Player/moving platform = `type: CANNON.Body.KINEMATIC` (set `velocity`) or set `body.position` yourself.
- Force/impulse: `body.applyImpulse(new CANNON.Vec3(0, 5, 0))` (instant kick), `applyForce` (every frame). Damping: `linearDamping`, `angularDamping` 0.1-0.4 so balls stop rolling forever.
- Events: `body.addEventListener('collide', (e) => { const v = e.contact.getImpactVelocityAlongNormal(); if (v > 3) playHit(); })`.
- Remove: `world.removeBody(body); scene.remove(mesh);` and do NOT dispose geometry/material shared by other meshes. Do it outside `world.step` (flag, then remove after).
- Wake/teleport: `body.position.set(...); body.velocity.setZero(); body.wakeUp()`.
- Cap bodies (~150 on phones); share ONE geometry + material per kind.
- Verified pile with spawn buttons: `skill("threejs-physics-collision", "cannon-pile")`.

## Raycaster, triggers, pickups
```js
// fragment
const ray = new THREE.Raycaster(new THREE.Vector3(x, y + 0.5, z), new THREE.Vector3(0, -1, 0), 0, 3);
const hit = ray.intersectObjects(groundMeshes, false)[0];      // pass an array of meshes, not the whole scene
if (hit) { groundY = hit.point.y; slopeNormal = hit.face.normal; }
```
Line of sight: ray from eye to target, blocked if first hit is not the target. Pickup/trigger = distance check `< 0.8` (cheap, no physics), then hide + score. Mouse picking: `ray.setFromCamera(pointerNdc, camera)`.

## Pitfalls
Objects fall through the floor: spawned overlapping it, `world.step` missing, or Plane not rotated. Jittery pile: step with variable dt only (`world.step(dt)` without fixed step), or tiny boxes. Meshes lag: copy AFTER `step`. Bodies explode: spawned inside each other. Slow: too many bodies, sleeping off.
