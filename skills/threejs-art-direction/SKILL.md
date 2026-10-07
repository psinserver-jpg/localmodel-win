---
name: threejs-art-direction
description: Make three.js scenes look designed, not like grey boxes - pick one visual style (low-poly, toon, clay, neon synthwave, realistic, voxel), use a real palette, lighting by time of day, fog and gradient sky, camera composition, motion polish, scroll-driven camera. Use for any 3D mood, atmosphere, style, beautiful-looking or portfolio/product-page request.
triggers: [art direction, 3d style, 3d look, mood, atmosphere, low poly, lowpoly, low-poly, diorama, synthwave, vaporwave, neon, cel shading, stylized, color palette, composition, juice, game feel, scroll animation, scroll driven, portfolio 3d, product showcase, hero scene, 분위기, 연출, 느낌있게, 예쁘게, 이쁘게, 감성, 로우폴리, 디오라마, 신스웨이브, 네온 느낌, 스타일, 색감, 팔레트, 구도, 카메라 연출, 스크롤 애니메이션, 스크롤 3d, 포트폴리오 3d, 제품 쇼케이스, 타격감]
priority: 47
---
# Art direction for three.js (r160)

## Decide first (write it down in 1 line): STYLE + PALETTE + TIME OF DAY
Grey boxes on a grey plane = no decision. Pick ONE style and keep every object in it.
| Style | Materials | Light / extras |
|---|---|---|
| Low-poly flat | `MeshStandardMaterial({flatShading:true, roughness:.9})`, 5-9 segments, jittered vertices | hemi 1.0 + warm sun 2.6, soft shadows, fog = sky bottom |
| Toon / cel | `MeshToonMaterial` 3-band gradientMap + inverted-hull outline | 1 strong directional, no hemi fill, flat bright palette |
| Soft clay | `MeshStandardMaterial roughness .85`, rounded geometry, pastel | big soft shadows (`radius 6`), hemi 1.3, `ACESFilmic` |
| Neon synthwave | dark `MeshBasic`/shader grid, emissive HDR colours | bloom (thr 1.0), fog, sunset sky shader, magenta+cyan only |
| Realistic PBR | Standard/Physical, `RoomEnvironment` env, textures | ACES, 3-point or sun, `envMap` intensity 0.6-1 |
| Voxel | `InstancedMesh` of boxes, `MeshLambertMaterial`, per-instance colour | hard directional, ambient 0.6, no outlines |

## Palettes (hex; use 60% base / 30% secondary / 10% accent)
- Sunny island (calm): sky `#6fb7ff`->`#ffe3c2`, grass `#7cc576`, sand `#f3d9a4`, water `#39b6d6`, roof `#e9654b`
- Synthwave (retro): bg `#12002b`, grid `#19d3ff`, magenta `#ff2d95`, sun `#ffd93b`, purple `#4b0f8c`
- Candy clay (playful): `#ffd6e0`, `#c1e1ff`, `#fff3b0`, `#b8f2e6`, accent `#ff6b9d`
- Midnight forest (mystery): bg `#0a1230`, trees `#12372a`, moon `#cfe0ff`, firefly `#ffe66d`, ground `#1b2a41`
- Desert dusk (warm): sky `#ff9a62`->`#4a2c6d`, sand `#e8b87a`, rock `#9b5b3c`, shadow `#3a2347`
- Arctic (clean): `#eaf6ff`, `#a8d8f0`, ice `#5fb4e0`, deep `#1d4e75`, accent `#ff7a59`
- Lava cave (danger): bg `#14070a`, rock `#3a1f1f`, lava `#ff5a00`, glow `#ffb703`
- Mono product (premium): bg `#15171c`, key `#ffffff`, rim `#6c8cff`, accent `#ff6b9d`
Never pure `#ffffff`/`#000000` for surfaces; shadows should be tinted (blue/purple), not black.

## Never flat grey: ground + sky + depth
- Sky = gradient (`CanvasTexture` 2x256 as `scene.background`, or a BackSide shader sphere); `scene.fog = new THREE.Fog(skyBottomColour, near, far)` with the SAME colour as the sky bottom so the horizon melts.
- Ground is coloured/varied (water plane, grass + sand ring, grid shader), never `0x808080`.
- Layer depth: foreground (small dark/blurred props near camera), midground (hero), background (mountains, clouds, fog layers). Overlap silhouettes.
- Time of day (numbers from `threejs-materials-lighting`): day sun `0xfff1d6` 2.4 high; golden `0xff9a4d` 3.0 low (y 4) + `0xffd2a1` hemi; night `0x8fb4ff` 0.9 + hemi `0x274a8a` 0.5 + warm point lamps `0xffb066`.

## Camera composition
Hero/product shots FOV 35-50 (flatter, premium), games 60-75. Low angle = powerful, high angle (30-45 deg) = readable diorama. Put the subject on a thirds line, look slightly past it; leave empty space where the title goes. Slow orbit or breathing dolly makes still scenes feel alive (`camera.position` on a circle, `lookAt` above centre).

## Readability and scale
Silhouette first: distinguishable shapes at 64 px (cone tree vs box house vs sphere rock). Keep 3-4 sizes only; player 1.0-1.8 m, door 2 m, tree 3-6 m. Accent colour only for what is interactive. Big objects slow, small objects fast.

## Juice (feel) - verified helpers in `skill("threejs-art-direction", "scroll-juice")`
Squash & stretch on land/pickup (0.35 s decaying wobble), `easeOutBack` pop-in for spawns, camera shake with trauma (squared decay), `damp()` smoothing for cameras, light flicker, particles on hit. Animate everything with easing, never linear.

## UI pairing
HTML over the canvas: one font, 2 sizes; titles `clamp(28px, 6vw, 64px)` with `text-shadow` glow in the accent colour; safe margins 16-24 px (`env(safe-area-inset-*)` on phones); `pointer-events:none` on overlays. Korean text: `font-family: "Pretendard","Noto Sans KR",sans-serif`.

## Scroll-driven 3D page, intro
Canvas `position:fixed`, a tall spacer div, `progress = scrollY / (scrollHeight - innerHeight)`, `CatmullRomCurve3.getPoint(progress, camera.position)`, ease toward the target with `damp`, `camera.lookAt(hero)`, toggle text sections by progress. Intro: fade a full-screen div out + start camera far and dolly in over 2 s with `easeOutCubic`.

## Verified full scenes (copy, then restyle)
`skill("threejs-art-direction", "island-diorama")` - low-poly island, gradient sky, fog, water, trees, soft shadows.
`skill("threejs-art-direction", "synthwave")` - neon grid sunset with bloom. `"scroll-juice"` - scroll camera + juice.
