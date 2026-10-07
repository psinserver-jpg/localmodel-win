---
name: motion-recipes
description: Working recipes for skeleton loaders, spinners, accordion height animation, count-up numbers, typing text, marquee, menu and modal transitions, stagger helpers, magnetic hover, progress bars, and View Transitions with fallback.
triggers: [skeleton, loader, spinner, accordion animation, count up, counter, typing effect, marquee, ticker, menu animation, modal animation, stagger, progress bar, view transition, page transition, ripple, shake, pulse, 스켈레톤, 로더, 스피너, 아코디언, 숫자 카운트, 타이핑 효과, 마키, 메뉴 애니메이션, 모달 애니메이션, 진행 바, 페이지 전환, 물결, 흔들림]
---
# Motion recipes

## Spinner and progress
```css
.spinner { width: 1.5rem; height: 1.5rem; border: 3px solid rgb(0 0 0 / .12); border-top-color: #2563eb; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.bar { height: 6px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }
.bar > i { display: block; height: 100%; width: 100%; background: #2563eb; transform-origin: left; transform: scaleX(var(--p, 0)); transition: transform 400ms cubic-bezier(.4, 0, .2, 1); }
.dots span { display: inline-block; width: 8px; height: 8px; margin: 0 2px; border-radius: 50%; background: currentColor; animation: bounce 1s ease-in-out infinite; animation-delay: calc(var(--i) * 120ms); }
@keyframes bounce { 0%, 80%, 100% { transform: translateY(0); opacity: .4; } 40% { transform: translateY(-6px); opacity: 1; } }
```
Progress via transform (`--p: .4` set from JS), never animate `width`.

## Skeleton screen
```html
<div class="sk-card" aria-busy="true" aria-label="불러오는 중">
  <div class="sk sk--img"></div><div class="sk sk--line"></div><div class="sk sk--line sk--short"></div>
</div>
```
```css
.sk { background: linear-gradient(90deg, #eceff3 25%, #f6f8fa 50%, #eceff3 75%); background-size: 200% 100%; animation: shimmer 1.4s linear infinite; border-radius: 8px; }
.sk--img { aspect-ratio: 16 / 9; } .sk--line { height: 1rem; margin-top: .75rem; } .sk--short { width: 60%; }
@keyframes shimmer { to { background-position: -200% 0; } }
@media (prefers-reduced-motion: reduce) { .sk { animation: none; } }
```
Swap in real content with a 200ms fade; keep identical dimensions to avoid layout shift. Dark mode: `#232833 / #2d3340`.

## Accordion without animating height
```html
<div class="acc"><button type="button" aria-expanded="false" aria-controls="a1">환불은 어떻게 하나요?</button>
<div class="acc__body" id="a1"><div>구매 후 7일 이내 설정 화면에서 바로 신청할 수 있어요.</div></div></div>
<script>
document.querySelectorAll('.acc > button').forEach((b) => {
  b.addEventListener('click', () => {
    const open = b.getAttribute('aria-expanded') === 'true';
    b.setAttribute('aria-expanded', String(!open));
  });
});
</script>
```
```css
.acc__body { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 250ms cubic-bezier(.4, 0, .2, 1); }
.acc__body > div { overflow: hidden; }
.acc > button[aria-expanded="true"] + .acc__body { grid-template-rows: 1fr; }
```
Fallback for old browsers: it simply jumps open/closed, still works.

## Count-up numbers
```html
<p class="stat"><strong data-count="12480">0</strong>명이 사용 중이에요</p>
<script>
function countUp(el, duration = 1400) {
  const target = Number(el.dataset.count);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = target.toLocaleString('ko-KR'); return; }
  const start = performance.now();
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);
  const tick = (now) => {
    const t = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(target * easeOut(t)).toLocaleString('ko-KR');
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => { if (e.isIntersecting) { countUp(e.target); io.unobserve(e.target); } });
}, { threshold: 0.6 });
document.querySelectorAll('[data-count]').forEach((el) => io.observe(el));
</script>
```
Add `font-variant-numeric: tabular-nums` so digits do not jitter; set `min-width` in `ch` for the number.

## Typing effect (single line)
```css
.type { display: inline-block; overflow: hidden; white-space: nowrap; border-right: 2px solid currentColor; width: 0;
  animation: typing 2.4s steps(18, end) forwards, caret .8s step-end infinite; }
@keyframes typing { to { width: 18ch; } }
@keyframes caret { 50% { border-color: transparent; } }
```
Korean glyphs are wider than `ch`: use `width: 18em` approx or JS slicing of the string instead.

## Marquee (logos)
```css
.marquee { overflow: hidden; mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent); }
.marquee__track { display: flex; width: max-content; gap: 3rem; animation: scroll 30s linear infinite; }
.marquee:hover .marquee__track { animation-play-state: paused; }
@keyframes scroll { to { transform: translateX(-50%); } }
@media (prefers-reduced-motion: reduce) { .marquee__track { animation: none; flex-wrap: wrap; width: auto; } }
```
Duplicate the logo list once inside the track so -50% loops seamlessly.

## Mobile menu and drawer
```css
.menu { position: fixed; inset: 0 0 0 auto; width: min(20rem, 85vw); transform: translateX(100%); visibility: hidden;
  transition: transform 300ms cubic-bezier(.4, 0, .2, 1), visibility 0s linear 300ms; }
.menu.is-open { transform: none; visibility: visible; transition-delay: 0s; }
.scrim { position: fixed; inset: 0; background: rgb(0 0 0 / .5); opacity: 0; pointer-events: none; transition: opacity 250ms linear; }
.scrim.is-open { opacity: 1; pointer-events: auto; }
```
`visibility` with delay keeps closed menus out of tab order.

## Modal enter/exit with discrete properties (progressive)
```css
dialog { opacity: 0; transform: translateY(8px) scale(.98); transition: opacity 200ms ease-out, transform 200ms ease-out, display 200ms allow-discrete, overlay 200ms allow-discrete; }
dialog[open] { opacity: 1; transform: none; }
@starting-style { dialog[open] { opacity: 0; transform: translateY(8px) scale(.98); } }
dialog::backdrop { background: rgb(0 0 0 / 0); transition: background 200ms, display 200ms allow-discrete, overlay 200ms allow-discrete; }
dialog[open]::backdrop { background: rgb(0 0 0 / .5); }
@starting-style { dialog[open]::backdrop { background: rgb(0 0 0 / 0); } }
```
Browsers without it just show/hide instantly.

## Micro-interactions
```css
.heart.is-on { animation: pop 350ms cubic-bezier(.34, 1.56, .64, 1); color: #e11d48; }
@keyframes pop { 0% { transform: scale(.7); } 60% { transform: scale(1.25); } 100% { transform: scale(1); } }
.shake { animation: shake 360ms cubic-bezier(.36, .07, .19, .97); }
@keyframes shake { 20%, 60% { transform: translateX(-6px); } 40%, 80% { transform: translateX(6px); } }
.link-u { background: linear-gradient(currentColor, currentColor) 0 100% / 0 2px no-repeat; transition: background-size 250ms cubic-bezier(.2, 0, 0, 1); }
.link-u:hover { background-size: 100% 2px; }
.switch::after { content: ""; position: absolute; width: 1.25rem; height: 1.25rem; border-radius: 50%; background: #fff; transition: transform 160ms cubic-bezier(.4, 0, .2, 1); }
.switch[aria-checked="true"]::after { transform: translateX(1.25rem); }
```
Invalid form: add `.shake` to the field, remove on `animationend`. Success: check icon with `stroke-dashoffset` from path length to 0 over 400ms.

## View Transitions (page and state changes)
Same-document (single file apps, tabs, theme toggle):
```js
function swap(update) {
  if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) { update(); return; }
  document.startViewTransition(update);
}
document.querySelectorAll('[data-view]').forEach((btn) => {
  btn.addEventListener('click', () => swap(() => {
    document.querySelectorAll('.view').forEach((v) => { v.hidden = v.id !== btn.dataset.view; });
  }));
});
```
```css
::view-transition-old(root), ::view-transition-new(root) { animation-duration: 250ms; animation-timing-function: cubic-bezier(.4, 0, .2, 1); }
.hero-img { view-transition-name: hero; }          /* shared element: same name on both states, unique per page */
@media (prefers-reduced-motion: reduce) { ::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) { animation: none !important; } }
```
Multi-page sites (Chrome/Safari): `@view-transition { navigation: auto; }` in CSS of every page. Unsupported browsers navigate normally; the fallback IS the normal behaviour, so never depend on it.
