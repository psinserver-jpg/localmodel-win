---
name: canvas-2d-game
description: Build complete, playable 2D browser games with the HTML5 Canvas (no libraries) - DPR-correct canvas, fixed-timestep loop, state machine, keyboard and touch input, AABB collision, tilemaps, scrolling camera, pixel art from code, particles, beeps, high score, pause, game over and restart. Use for any canvas 2D game, runner, platformer, breakout, shooter or arcade request that is not 3D.
triggers: [canvas, canvas game, canvas 2d, 2d game, 2d, 2d game, html5 canvas, 캔버스, 2d 게임, 캔버스 게임, 평면 게임, 플랫폼, 플랫포머, platformer, 러너, runner, endless runner, 벽돌깨기, breakout, 핑퐁, pong, 슈팅, shooter, 스네이크, snake, 횡스크롤, side scroller, 타일맵, tilemap, sprite, 스프라이트, 픽셀, pixel art, 도트, 아케이드, arcade, 점프 게임, 장애물 피하기, 간단한 게임, 웹 게임, 게임 만들어]
priority: 46
---
# Canvas 2D games that are really playable

Single `index.html`, inline `<script>` (no modules/imports needed), no libraries, works by double-click. UI text in the user's language. For 3D use `threejs-game` instead.
**Runner / dodge / endless game: read `skill("canvas-2d-game", "dino-runner")`, copy it, change theme + rules. Platformer / tiles / scrolling: `skill("canvas-2d-game", "tilemap-platformer")`.** Do not write these from scratch. Breakout/pong/snake/shooter: use the architecture below.

## A game is done only when all of this exists
1. Start screen (name + controls), HUD (score, best, lives), game-over screen (score + best) and restart WITHOUT reload via a `startGame()` that resets EVERYTHING (arrays `length = 0`, timers, speed). 0.4-0.5 s guard so a held key does not restart instantly.
2. State machine `'ready' | 'playing' | 'over'` (+ `'won'`, `paused`). `update(dt)` returns immediately unless playing.
3. Keyboard AND pointer/touch (`pointerdown/up`, `touch-action:none` on body). `preventDefault` on Space/arrows; ignore `e.repeat`; clear held keys on `blur`; pause on `document.hidden`.
4. Difficulty ramp (speed/spawn rate grows, capped), best score in `localStorage` inside try/catch.
5. Feedback: particles on hit/collect, screen shake on death, beeps (WebAudio, created on first input, wrapped in try/catch).
6. Winnable: check the jump math (below) and spacing of hazards.

## Hard rules
- **DPR-correct canvas**: draw in a fixed logical size (e.g. 800x300); `canvas.width = cssWidth * dpr`, `ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0)`; re-run on `resize`. Size with CSS `width: min(100vw, 900px, calc(100vh * ratio)); aspect-ratio: W / H`. Pixel art: `image-rendering: pixelated`, `ctx.imageSmoothingEnabled = false`.
- **Fixed timestep**: `acc += min(dt, 0.1); while (acc >= 1/60) { update(1/60); acc -= 1/60 } draw()`. Physics never depends on frame rate; `requestAnimationFrame` gives `now` in ms.
- Entities = plain objects in arrays (`obstacles`, `bullets`, `particles`); loop backwards and `splice` to remove. Cap array sizes. Never allocate in hot loops more than needed.
- **Coordinates**: store `y` as height above ground (runner) or canvas y (tiles) - pick one and draw with one conversion.
- **AABB**: `a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y`. Shrink hitboxes 10-20% per side so it feels fair. Tile collision: move X then resolve, move Y then resolve (one axis at a time).
- Smooth feel: acceleration toward target speed, coyote time 0.1 s, jump buffer 0.12 s, release early = short hop (`vy = max(vy, -200)`).
- Use `Math.round` for pixel-art positions; draw sprites from string rows (`'#'` = pixel) as one `fillRect` per horizontal run (0.5 px overlap) to avoid seam lines when scaled.
- Draw order: background, ground/tiles, entities, particles, HUD, overlays. Text with `ctx.textAlign` and a font that has Korean (`system-ui`).

## Be winnable - check the math (this exact bug is common)
Gravity `g`, take-off speed `v`: apex `h = v^2/(2g)`, airtime `T = 2v/g`. Example `g=2600, v=900` -> apex 156 px, T 0.69 s. An obstacle is clearable only if `height < 0.55 * apex`; width + player width must fit inside `speed * (time above obstacle)`; gap between hazards >= `speed * T + 150` px; spikes/enemies must not sit right after a gap or under a low platform (a platform with clearance < player height + jump need makes jumps bump). Compute `MAX_OBSTACLE_H` in code from the constants and spawn within it. Test with a bot through `window.__game` (state, entities, `press()`).

## Skeleton (verified in both games)
```js
// fragment
const W = 800, H = 300, STEP = 1 / 60;
function fit() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2), r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
}
window.addEventListener('resize', fit); fit();
let mode = 'ready', acc = 0, last = 0;
function startGame() { resetGame(); mode = 'playing'; }
function frame(now) {
  requestAnimationFrame(frame);
  acc += Math.min((now - last) / 1000, 0.1); last = now;
  while (acc >= STEP) { update(STEP); acc -= STEP; }
  draw();
}
requestAnimationFrame((t) => { last = t; frame(t); });
```
Tilemap: `const LEVEL = ['   ###', ...]` strings, `solid(c, r)` lookup, draw only visible columns `floor(camX / T)..ceil((camX + W) / T)`, camera `camX += (target - camX) * (1 - Math.exp(-8 * dt))` clamped to the map. More recipes (breakout, pong, snake, shooter, sprite sheets, sound): `skill("canvas-2d-game", "patterns")`.

## Pitfalls
Blurry canvas (no DPR) - physics tied to frame rate - tunnelling through thin walls at high speed (clamp step, move in small steps) - restart leaves old obstacles/timers - key stuck after alt-tab - space scrolls the page - audio throws before a user gesture (create it lazily) - `localStorage` throws in private mode - touch ignored (only keyboard) - unclearable obstacle - text hard-coded in English.
