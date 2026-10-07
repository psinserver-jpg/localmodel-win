---
name: motion-animation
description: Purposeful UI motion in plain CSS/JS: duration and easing tables, transitions, keyframes, staggered and scroll reveals, micro-interactions, skeleton loaders, View Transitions, count-up numbers, reduced-motion handling, performance, Web Animations API and GSAP via CDN. Use for animation, transitions, hover effects and scroll effects.
triggers: [animation, animate, transition, motion, keyframes, easing, ease, cubic-bezier, hover effect, micro-interaction, scroll reveal, scroll animation, fade in, slide in, stagger, parallax, skeleton, loader, spinner, page transition, view transition, count up, counter animation, reduced motion, gsap, web animations, intersection observer, 애니메이션, 트랜지션, 모션, 움직임, 호버 효과, 스크롤 효과, 스크롤 애니메이션, 페이드, 슬라이드, 순차, 로딩, 스켈레톤, 스피너, 페이지 전환, 숫자 카운트, 부드럽게, 움직이는, 인터랙션]
priority: 46
---
# Motion and Animation

## Hard rules
1. Motion has a purpose: feedback (press), orientation (where did it come from), attention (new item), or delight (rare). If none, remove it.
2. Animate ONLY `transform` and `opacity` (GPU, no layout). Never animate `width/height/top/left/margin`; to open/close height use `grid-template-rows: 0fr -> 1fr` or `max-height` as last resort. `filter`/`box-shadow` animate sparingly.
3. Durations: press/hover feedback 100-150ms; small UI (tooltip, toggle) 150-200ms; panels/dropdowns/modals 200-300ms; large page/hero entrance 400-600ms; never > 700ms for UI. Exit faster than enter (about 70%).
4. Easing: enter/appear = ease-out `cubic-bezier(.2, 0, 0, 1)`; exit = ease-in `cubic-bezier(.4, 0, 1, 1)`; move on screen = `cubic-bezier(.4, 0, .2, 1)`; playful overshoot `cubic-bezier(.34, 1.56, .64, 1)`. Never `linear` except spinners/progress/shimmer. Never default `ease` for anything important.
5. ALWAYS add the reduced-motion guard (below). Keep content visible without JS: hide-then-reveal only under `.js` class set in `<head>`.
6. Stagger: 40-80ms per item, cap total at 600ms (use `min()`).
7. One signature motion per page (e.g. hero entrance + scroll reveal). Not everything bounces.
8. Hover only on `@media (hover: hover)`; touch uses `:active` feedback. Press = `transform: scale(.97)` 100ms.
9. Loading: < 100ms nothing; 100ms-1s spinner or button busy state; > 1s skeleton matching the final layout size (no layout shift).
10. Do not use `will-change` globally; set it on elements that are about to animate and remove after. Use `transform: translateZ(0)` hacks never.
11. Use `animation-fill-mode: both` for entrances; use `animation-delay` via CSS variable `--i`.
12. Prefer CSS; JS only for scroll triggers (IntersectionObserver), count-up, sequences (Web Animations API), or complex timelines (GSAP CDN `https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js`).

## Copy-paste core (reduced-motion safe)
```html
<script>document.documentElement.classList.add('js');</script>
<section class="features">
  <article class="reveal" style="--i:0"><h3>빠른 시작</h3><p>3분이면 설정이 끝나요.</p></article>
  <article class="reveal" style="--i:1"><h3>안전한 보관</h3><p>모든 데이터를 암호화해요.</p></article>
  <article class="reveal" style="--i:2"><h3>팀 협업</h3><p>실시간으로 함께 편집해요.</p></article>
</section>
<script>
const items = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
  items.forEach((el) => io.observe(el));
} else {
  items.forEach((el) => el.classList.add('is-visible'));
}
</script>
```
```css
:root { --ease-out: cubic-bezier(.2, 0, 0, 1); --ease-in: cubic-bezier(.4, 0, 1, 1); --ease-std: cubic-bezier(.4, 0, .2, 1); --ease-spring: cubic-bezier(.34, 1.56, .64, 1); }
.js .reveal { opacity: 0; transform: translateY(16px); }
.js .reveal.is-visible {
  opacity: 1; transform: none;
  transition: opacity 500ms var(--ease-out), transform 500ms var(--ease-out);
  transition-delay: calc(min(var(--i, 0), 8) * 70ms);
}
.btn { transition: transform 120ms var(--ease-out), background-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out); }
.btn:active { transform: scale(.97); }
@media (hover: hover) {
  .btn:hover { transform: translateY(-1px); box-shadow: 0 6px 16px -6px rgb(0 0 0 / .3); }
  .card:hover { transform: translateY(-4px); box-shadow: 0 16px 32px -12px rgb(0 0 0 / .25); }
}
.card { transition: transform 240ms var(--ease-out), box-shadow 240ms var(--ease-out); }
@keyframes fade-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.hero > * { animation: fade-up 600ms var(--ease-out) both; animation-delay: calc(var(--i, 0) * 80ms); }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; transition-delay: 0ms !important; scroll-behavior: auto !important; }
  .js .reveal { opacity: 1; transform: none; }
}
```

## Quick table (what to use)
| Need | Duration | Easing | Properties |
|---|---|---|---|
| Button hover/press | 120ms | out | transform, background |
| Toggle/checkbox | 160ms | std | transform, background |
| Dropdown/tooltip | 180ms | out (exit in) | opacity, transform: translateY(-4px) |
| Modal in / out | 280 / 200ms | out / in | opacity, scale .96 -> 1 |
| Drawer | 300ms | std | translateX(-100% -> 0) |
| Toast | 240ms | out | opacity, translateY(8px) |
| Scroll reveal | 500ms | out | opacity, translateY(16px) |
| Hero entrance | 600ms, stagger 80ms | out | opacity, translateY(12px) |
| Accordion | 250ms | std | grid-template-rows 0fr -> 1fr |
| Page transition | 250-350ms | std | View Transitions crossfade |

## Pitfalls
- `transition: all` animates layout props by accident; list properties.
- Animating `box-shadow` on 50 cards janks: fade a pseudo-element's opacity instead.
- Reveal stuck invisible when JS fails or the observer never fires: hide only under `.js` and add the no-IO fallback above.
- Infinite animations (pulse, float) distract; allow at most one, pause with `animation-play-state` off-screen, remove under reduced motion.
- Parallax by scroll listeners is heavy; use `transform` with `requestAnimationFrame` or CSS `animation-timeline: scroll()` behind `@supports`.
- Auto-playing carousels: provide pause, never faster than 5s.
- Page transitions (View Transitions API), skeleton, count-up, Web Animations API, GSAP, scroll-driven CSS: see reference/motion-recipes.md and reference/advanced-motion.md.
