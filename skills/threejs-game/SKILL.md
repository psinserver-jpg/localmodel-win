---
name: threejs-game
description: Build complete, playable 3D browser games with three.js - game states, input (keyboard and touch), fair rules, collisions, spawning, score, game over and restart. Includes a tested 3D dino endless runner to copy. Use for any three.js game, runner, platformer, shooter or arcade request.
triggers: [three.js game, threejs game, 3d game, 3d 게임, 게임, game, 공룡, 공룡게임, 공룡 게임, dino, dinosaur, runner, endless runner, 러너, 달리기, 점프, jump, obstacle, 장애물, platformer, 플랫포머, shooter, 슈팅, racing, 레이싱, arcade, 아케이드, score, 점수, game over, 게임 오버, 캐릭터 조작, 무한, 3d 액션, 장애물 피하기]
priority: 57
---
# three.js games that are really playable

FIRST read `threejs-basics` (single index.html, import map, black-screen checklist). Then: **for an endless runner / dodge / jump game, read the full working code with the `skill` tool: `skill("threejs-game", "dino-runner")`, copy it, and change theme and rules.** Do not write a runner from scratch. More recipes: `skill("threejs-game", "game-patterns")`.

## A game is only done when all of this exists
1. Start screen with the game name and the controls (in the user's language), start on key/click/tap.
2. Live HUD: score (+ best, saved in `localStorage`), optional lives/timer. HTML overlay, not 3D text.
3. Core loop with `dt`: `update(dt)` then render. State machine `'ready' | 'playing' | 'over'`.
4. Difficulty ramp: speed/spawn rate grows with time, capped (e.g. 12 -> 28 m/s).
5. Collision -> game-over screen with score + best, a restart that needs no page reload (a `startGame()` that resets EVERYTHING and removes old objects), and a ~0.4 s guard so a held key does not restart instantly.
6. Input: keyboard (Space/Arrows/WASD) AND pointer/touch (`pointerdown`), `touch-action:none` on body. Prevent default on Space/Arrows so the page does not scroll.
7. Cleanup: remove obstacles that left the screen (`scene.remove`), cap object counts, pause when `document.hidden`.
8. Sky/fog/ground/shadows so it does not look like grey boxes (see `threejs-art-direction`).

## The game must be WINNABLE - check the math before you ship
- Jump with gravity `g` and take-off speed `v`: apex `h = v^2/(2g)`, airtime `T = 2v/g`. Example `g=45, v=17` -> apex 3.2 m, airtime 0.76 s.
- An obstacle of height `oh` is clearable only if `oh < 0.55 * apex` (you must be ABOVE it while crossing its whole width). A 2.7 m cactus with a 2.7 m apex is IMPOSSIBLE (this exact bug happens often).
- Time spent above `oh`: solve `v*t - g*t^2/2 = oh`; the two roots give `dt_clear`. Distance covered meanwhile `= speed * dt_clear` must be >= 2 x (obstacle hit width + player width). Check it at the MAXIMUM speed.
- Gap between obstacles >= `speed * T + 4` m, otherwise two obstacles can need two jumps at once.
- Hitboxes: use simple boxes (centre, half-width, bottom, top), shrink them by ~15-20% so it feels fair. Ducking lowers the player's top.

## Skeleton (state machine + loop; everything else plugs into it)
```js
// fragment
const state = { mode: 'ready', speed: 12, score: 0 };
function startGame() { clearWorld(); state.mode = 'playing'; state.speed = 12; state.score = 0; hideMenu(); }
function endGame() { state.mode = 'over'; overAt = performance.now(); saveBest(); showMenu('게임 오버'); }
function update(dt) {
  if (state.mode !== 'playing') return;
  state.speed = Math.min(MAX_SPEED, state.speed + dt * 0.25);
  state.score += state.speed * dt * 0.8;
  movePlayer(dt); moveWorld(dt); spawnIfNeeded(dt);
  if (collides()) endGame();
}
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  update(dt); animateScenery(dt); renderer.render(scene, camera);
}
```

## Build characters from primitives (no downloads needed)
Group of `BoxGeometry`/`CylinderGeometry`/`SphereGeometry` with `flatShading: true`, one colour per body part, `castShadow = true`; pivots (`Group`) for legs/arms so you can rotate them for run cycles (`leg.rotation.z = Math.sin(t * speed) * 0.9`).

## Variations on the runner
- **3-lane runner**: player `x` lerps to lane `-2.5, 0, 2.5`; obstacles spawn in a random lane; swipe/arrows change lane.
- **Flappy**: constant forward speed, tap sets `vy = +8`, gravity pulls down, pipes = box pairs with a gap; hit = game over.
- **Top-down shooter**: camera above (`position.y=20`, `lookAt(0,0,0)`), WASD moves, click shoots bullets (pool them), enemies chase with `dir.subVectors(player, enemy).normalize()`.
- **Racing**: car moves along -Z at speed, steering changes `x`, road segments recycled when behind the camera.
- **Platformer**: gravity + `onGround` check against box tops, coyote time 0.1 s, camera follows X smoothly (`cam.x += (p.x - cam.x) * (1 - Math.exp(-6 * dt))`).

## Mistakes that break games
Frame-based speeds (use `dt`) - not resetting arrays/timers on restart - creating geometries/materials on every spawn (create once, reuse) - forgetting `scene.remove` so objects pile up - two keydown handlers - `e.repeat` auto-jumping - no touch support - text hard-coded in English - collision using positions of groups whose origin is not the centre.
