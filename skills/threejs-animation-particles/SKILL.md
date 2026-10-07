---
name: threejs-animation-particles
description: Animate three.js scenes - dt-based motion, damping/easing, tweens (own or GSAP), camera moves, GLTF AnimationMixer, plus THREE.Points particles (fountain, burst, snow, rain, stars, fireflies, trails) and InstancedMesh crowds. Use for any three.js animation, particle, effect, camera movement or screen-shake request.
triggers: [three.js animation, threejs animation, animation, animate, 애니메이션, particle, particles, 파티클, points, 입자, snow, 눈 내리, rain, 비 내리, fireflies, 반딧불, stars, 별, explosion, 폭발, burst, fountain, 분수, trail, 궤적, 불꽃, 폭죽, firework, tween, gsap, easing, 이징, lerp, camera move, 카메라 이동, 카메라 연출, fly-through, 플라이스루, mixer, animationmixer, instancedmesh, 인스턴스, screen shake, 화면 흔들림, 효과, effect, effects, 움직임]
priority: 50
---
# three.js animation and particles (r160)

Setup, import map and black-screen checklist: `threejs-basics`. This skill = motion and effects.

## Hard rules
1. Every motion uses `dt` (`Math.min(clock.getDelta(), 0.05)`) - never "+= 0.01 per frame". Procedural loops use `t += dt` or `clock.elapsedTime`.
2. Smoothing that is frame-rate independent: `damp(a, b, lambda, dt) = lerp(a, b, 1 - Math.exp(-lambda * dt))` (lambda 3-10). Plain `lerp(a, b, 0.1)` speeds up/slows down with FPS.
3. ONE `THREE.Points` (or InstancedMesh) per effect, typed arrays allocated ONCE, a ring buffer reuses dead slots. Never `new Vector3`/`new Mesh` per particle per frame, never add/remove meshes for sparks.
4. After editing positions/colors: `geometry.attributes.position.needsUpdate = true` (same for color). Set `points.frustumCulled = false` for moving particles.
5. Glow look: `PointsMaterial({ map: softDot, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, vertexColors: true, size })`. Without a round texture particles are ugly squares. Draw the texture on a canvas (no files needed). Additive fades by darkening colour, NOT opacity; normal blending (snow) fades by opacity.
6. `size` is world units when `sizeAttenuation: true` (0.1-0.4 typical); pixels when false (stars: 1-2).
7. Static stars/dust are never updated; only animate what moves. Cap counts: 3000-10000 Points are fine, mobile 2000.
8. Animate on the object pivot (Group), not mesh geometry. Wrap, don't spawn: snow below y=0 re-enters at the top.
9. Camera: set position, then `lookAt`. Do not fight OrbitControls: apply shake AFTER `controls.update()`, and disable it during scripted moves (`controls.enabled = false`).

## Pick the tool
| Need | Use |
|---|---|
| bob / sway / breathe / pulse | `y = base + Math.sin(t * speed) * amp`; breathe `scale = 1 + Math.sin(t*2)*0.03` |
| A to B with easing | own `tween()` or GSAP (`skill("threejs-animation-particles", "camera-tween-mixer")`) |
| follow a target smoothly | `camera.position.x = damp(camera.position.x, target.x, 5, dt)` |
| GLTF clips | `AnimationMixer` + `mixer.update(dt)` (see reference) |
| thousands of identical things | `InstancedMesh` + `setMatrixAt` + `instanceMatrix.needsUpdate = true` |
| sparks, smoke, snow, stars | `THREE.Points` as below |

## Core pieces (verified)
```js
// fragment
const damp = (a, b, lambda, dt) => THREE.MathUtils.lerp(a, b, 1 - Math.exp(-lambda * dt));
function softDot() {                          // round glow sprite, no image file
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.4, 'rgba(255,255,255,0.5)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}
// ring buffer emit: slot i = next; next = (next + 1) % max;  life[i] = maxLife[i] = seconds
// update: if (life[i] <= 0) continue; life -= dt; vel.y += gravity * dt; pos += vel * dt;
//         color = base * (life / maxLife)   <- additive fade
// emit per second independent of FPS: acc += dt * rate; while (acc >= 1) { acc -= 1; emit(); }
let shake = 0;                                // on hit: shake = 0.4
// after controls.update():  camera.position.x += (Math.random() - 0.5) * shake * 0.3; shake = Math.max(0, shake - dt * 1.5);
```
Full runnable fountain + click bursts + shake: `skill("threejs-animation-particles", "particles")`. Snow + fireflies + stars + InstancedMesh trees: `skill("threejs-animation-particles", "snow-fireflies")`. Easing/tween/GSAP/mixer/scroll-driven camera path: `skill("threejs-animation-particles", "camera-tween-mixer")`. COPY those pages and change theme.

## Recipes
- Burst: 150-300 particles, random direction (`acos(2r-1)` for a sphere), speed 2-7, life 0.8-1.6 s, gravity -6.
- Trail: emit 1-3 particles per frame at the moving object's position with ~0 velocity, life 0.5 s, smaller size.
- Rain: Points, fall 15-25 m/s, tiny size, or `LineSegments` streaks; wrap at y<0.
- Fireflies: base position + sine drift with per-particle phase; pulse `material.opacity`.
- Crowd: InstancedMesh, one matrix per item, update matrices only for moving ones.

## Pitfalls
Particles are squares (no `map`) - invisible (`depthWrite` true hides them behind each other, `size` too small, `frustumCulled` culling) - updates not showing (`needsUpdate` missing) - speed differs per machine (no dt) - memory growth (allocating in the loop) - shake drifting the camera (apply after controls, never accumulate) - tweens fighting each other (one tween per property) - mixer not moving (`mixer.update(dt)` missing) - GSAP import without the import-map entry `"gsap": "https://cdn.jsdelivr.net/npm/gsap@3.12.5/+esm"`.
