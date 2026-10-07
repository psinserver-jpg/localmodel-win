---
name: advanced-motion
description: Web Animations API, GSAP via CDN (timelines, ScrollTrigger), scroll-driven CSS animations, parallax, hero text reveal, FLIP list reordering, performance checklist and reduced-motion patterns.
triggers: [gsap, scrolltrigger, web animations api, waapi, element.animate, timeline, scroll driven, animation-timeline, parallax, flip animation, list reorder, text reveal, hero animation, performance, will-change, reduced motion, prefers-reduced-motion, 지에스에이피, 타임라인, 스크롤 연동, 패럴랙스, 텍스트 등장, 히어로 애니메이션, 성능, 모션 줄이기, 애니메이션 성능]
---
# Advanced motion

## Web Animations API (no library)
```js
const card = document.querySelector('.card');
const anim = card.animate(
  [{ opacity: 0, transform: 'translateY(16px)' }, { opacity: 1, transform: 'none' }],
  { duration: 500, easing: 'cubic-bezier(.2, 0, 0, 1)', fill: 'both' }
);
anim.finished.then(() => console.log('done'));

// stagger a list
document.querySelectorAll('.list > li').forEach((li, i) => {
  li.animate([{ opacity: 0, transform: 'translateX(-12px)' }, { opacity: 1, transform: 'none' }],
    { duration: 400, delay: Math.min(i * 60, 600), easing: 'cubic-bezier(.2, 0, 0, 1)', fill: 'backwards' });
});

// remove an element with an exit animation
async function removeItem(el) {
  await el.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'scale(.96)' }], { duration: 180, easing: 'cubic-bezier(.4, 0, 1, 1)' }).finished;
  el.remove();
}
```
`anim.pause() / play() / reverse() / cancel()` are available; `fill: 'both'` keeps the end state.

## FLIP (smooth list reorder / layout change)
```js
function flip(container, mutate) {
  const kids = [...container.children];
  const first = new Map(kids.map((k) => [k, k.getBoundingClientRect()]));
  mutate();
  [...container.children].forEach((k) => {
    const f = first.get(k);
    if (!f) return;
    const l = k.getBoundingClientRect();
    const dx = f.left - l.left;
    const dy = f.top - l.top;
    if (dx || dy) k.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: 'none' }], { duration: 300, easing: 'cubic-bezier(.4, 0, .2, 1)' });
  });
}
// usage: flip(listEl, () => listEl.append(listEl.firstElementChild));
```

## Scroll-driven animations (CSS only, progressive)
```css
.progress { position: fixed; inset: 0 0 auto 0; height: 3px; background: #2563eb; transform-origin: left; transform: scaleX(0); z-index: 500; }
@supports (animation-timeline: scroll()) {
  .progress { animation: grow linear both; animation-timeline: scroll(root); }
  @keyframes grow { to { transform: scaleX(1); } }
  .reveal-sd { animation: sd-in linear both; animation-timeline: view(); animation-range: entry 0% entry 60%; }
  @keyframes sd-in { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: none; } }
}
@media (prefers-reduced-motion: reduce) { .progress { display: none; } .reveal-sd { animation: none; } }
```
Without support the bar stays hidden at scaleX(0) and elements stay visible: the fallback is "no effect", acceptable.

## Parallax (cheap)
```css
.parallax { overflow: hidden; position: relative; }
.parallax > img { position: absolute; inset: -10% 0; width: 100%; height: 120%; object-fit: cover; will-change: transform; }
```
```js
const layer = document.querySelector('.parallax > img');
if (layer && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  let ticking = false;
  addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const r = layer.parentElement.getBoundingClientRect();
      layer.style.transform = `translate3d(0, ${(r.top * -0.15).toFixed(1)}px, 0)`;
      ticking = false;
    });
  }, { passive: true });
}
```
Max speed factor 0.1-0.25; never parallax text.

## Hero headline word reveal (split without a library)
```html
<h1 class="split" aria-label="오늘의 일정을 한눈에">오늘의 일정을 한눈에</h1>
<script>
const h = document.querySelector('.split');
const words = h.textContent.trim().split(/\s+/);
h.setAttribute('aria-label', words.join(' '));
h.textContent = '';
words.forEach((w, i) => {
  const s = document.createElement('span');
  s.className = 'w';
  s.setAttribute('aria-hidden', 'true');
  s.style.setProperty('--i', i);
  s.textContent = w + ' ';
  h.append(s);
});
</script>
```
```css
.split .w { display: inline-block; opacity: 0; transform: translateY(.6em); animation: w-in 700ms cubic-bezier(.2, 0, 0, 1) forwards; animation-delay: calc(var(--i) * 90ms + 150ms); }
@keyframes w-in { to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .split .w { animation: none; opacity: 1; transform: none; } }
```
Split by words, not letters, for Korean (letter splits break syllable shaping and `keep-all`).

## GSAP via CDN
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
<script>
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
if (window.gsap && !reduce) {
  gsap.registerPlugin(ScrollTrigger);
  const tl = gsap.timeline({ defaults: { ease: 'power3.out', duration: 0.7 } });
  tl.from('.hero h1', { y: 30, opacity: 0 })
    .from('.hero p', { y: 20, opacity: 0 }, '-=0.4')
    .from('.hero .btn', { y: 16, opacity: 0, stagger: 0.1 }, '-=0.4');
  gsap.utils.toArray('.section').forEach((sec) => {
    gsap.from(sec.querySelectorAll('.card'), {
      y: 40, opacity: 0, duration: 0.6, stagger: 0.12, ease: 'power2.out',
      scrollTrigger: { trigger: sec, start: 'top 80%', once: true },
    });
  });
}
</script>
```
Guard `window.gsap` so the page still works offline; elements must be visible by default in CSS (GSAP `from` sets the hidden state itself). Pin/scrub only on desktop: `ScrollTrigger.matchMedia` or `gsap.matchMedia()`.

## Performance checklist
- Compositor-only: `transform`, `opacity`. Everything else triggers layout or paint.
- `will-change: transform` only on elements animating right now (add on `pointerenter`, remove on `transitionend`); too many layers eat memory.
- Read layout (`getBoundingClientRect`) then write styles, never interleave in a loop; batch inside `requestAnimationFrame`.
- Scroll handlers `{ passive: true }`; prefer IntersectionObserver over scroll events.
- Large blurs (`backdrop-filter`, `filter: blur(40px)`) on moving elements are expensive; keep them static.
- Animate small areas; avoid full-viewport fixed gradient animations.
- Test with CPU 4x throttling; target steady 60fps, no animation > 1s except loaders.

## Reduced-motion patterns
```js
const prefersReduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const dur = (ms) => (prefersReduced() ? 0 : ms);
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => document.documentElement.classList.toggle('reduce-motion', e.matches));
```
Reduce means "less", not "none": keep opacity fades (short), remove movement, parallax, auto-play, bounce and big scaling. Never hide content or delay interactions because of it.
