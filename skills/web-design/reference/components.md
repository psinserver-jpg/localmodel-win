---
name: components
description: Production-quality accessible HTML+CSS+JS for navbar with mobile menu, hero, buttons, cards, pricing, testimonial, FAQ, form validation, footer, modal dialog and tabs.
triggers: [component, navbar, nav, navigation, menu, hamburger, header, hero, button, card, pricing, testimonial, faq, accordion, form, contact form, validation, footer, modal, dialog, popup, tabs, 컴포넌트, 버튼, 카드, 메뉴, 네비게이션, 헤더, 푸터, 폼, 모달, 팝업, 탭, 가격표, 아코디언]
---
# Components

All snippets use the tokens from `css-foundation.md` (`--color-*`, `--space-*`, `--step-*`, `--radius*`, `--shadow-*`, `--dur*`, `--ease`). Example copy is English; always rewrite it in the user's language for the real business. Put this in `<head>` so JS-only styles never hide content when JS fails:
```html
<script>document.documentElement.classList.add('js');</script>
```
Put all JS in one `<script>` at the end of `<body>`; each block null-checks its elements.

## 1. Buttons

```css
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2);
  min-height: 44px; padding: 0.75rem 1.25rem;
  border: 1px solid transparent; border-radius: var(--radius);
  font-weight: 600; font-size: 1rem; line-height: 1.2; text-align: center; text-decoration: none;
  transition: background-color var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease),
              color var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease);
}
.btn, .btn:hover { text-decoration: none; }
.btn:active { transform: translateY(1px); }
.btn-primary { background: var(--color-primary); color: var(--color-on-primary); }
.btn-primary:hover { background: var(--color-primary-hover); color: var(--color-on-primary); }
.btn-secondary { background: transparent; color: var(--color-text); border-color: var(--color-border-strong); }
.btn-secondary:hover { background: var(--color-surface); color: var(--color-text); }
.btn-ghost { background: transparent; color: var(--color-primary); }
.btn-ghost:hover { background: color-mix(in srgb, var(--color-primary) 10%, transparent); color: var(--color-primary); }
.btn-lg { min-height: 52px; padding: 0.95rem 1.75rem; font-size: 1.0625rem; }
.btn:disabled, .btn[aria-disabled="true"] { opacity: 0.55; pointer-events: none; }
.icon-btn {
  display: inline-grid; place-items: center; width: 44px; height: 44px;
  border: 0; border-radius: var(--radius); background: transparent; color: var(--color-text);
}
.icon-btn:hover { background: var(--color-surface); }
```
```html
<a class="btn btn-primary btn-lg" href="#signup">Start 14-day trial</a>
<button class="btn btn-secondary" type="button">Book a demo</button>
```

## 2. Navbar with accessible mobile menu

```html
<header class="site-header">
  <div class="container nav">
    <a class="brand" href="#top">
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="currentColor"/><path d="M9 21V11l7 6 7-6v10" fill="none" stroke="var(--color-bg)" stroke-width="2.5" stroke-linejoin="round"/></svg>
      <span>Mintline</span>
    </a>
    <button class="icon-btn nav-toggle" type="button" aria-expanded="false" aria-controls="site-menu" aria-label="Open menu">
      <svg class="i-open" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      <svg class="i-close" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
    </button>
    <nav class="nav-menu" id="site-menu" aria-label="Main">
      <ul role="list">
        <li><a href="#features">Features</a></li>
        <li><a href="#pricing">Pricing</a></li>
        <li><a href="#faq">FAQ</a></li>
      </ul>
      <a class="btn btn-primary" href="#signup">Start free</a>
    </nav>
  </div>
</header>
```
```css
.site-header {
  position: sticky; top: 0; z-index: 50;
  background: color-mix(in srgb, var(--color-bg) 88%, transparent);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--color-border);
}
.nav { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--space-4); min-height: var(--header-h); }
.brand { display: inline-flex; align-items: center; gap: var(--space-2); font-weight: 700; font-size: 1.125rem; color: var(--color-text); text-decoration: none; }
.nav-menu ul { display: flex; flex-wrap: wrap; gap: var(--space-1); padding: 0; }
.nav-menu a:not(.btn) {
  display: flex; align-items: center; min-height: 44px; padding-inline: var(--space-3);
  color: var(--color-text); text-decoration: none; font-weight: 500; border-radius: var(--radius-sm);
}
.nav-menu a:not(.btn):hover { background: var(--color-surface); color: var(--color-text); }
.nav-menu a[aria-current="page"] { color: var(--color-primary); }
.nav-toggle { display: none; }
.i-close, .nav-toggle[aria-expanded="true"] .i-open { display: none; }
.nav-toggle[aria-expanded="true"] .i-close { display: block; }

/* Mobile, JS available: collapse into a panel */
@media (max-width: 767.98px) {
  .js .nav-toggle { display: inline-grid; }
  .js .nav-menu { display: none; }
  .js .nav-menu.is-open {
    display: grid; gap: var(--space-4);
    position: absolute; inset: 100% 0 auto 0;
    padding: var(--space-4) var(--gutter) var(--space-6);
    background: var(--color-bg); border-bottom: 1px solid var(--color-border); box-shadow: var(--shadow-lg);
  }
  .js .nav-menu.is-open ul { flex-direction: column; }
}
@media (min-width: 768px) {
  .nav-menu { display: flex; align-items: center; gap: var(--space-5); }
}
```
```js
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.getElementById('site-menu');
if (navToggle && navMenu) {
  const setOpen = (open) => {
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    navMenu.classList.toggle('is-open', open);
  };
  navToggle.addEventListener('click', () => setOpen(navToggle.getAttribute('aria-expanded') !== 'true'));
  navMenu.addEventListener('click', (e) => { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navMenu.classList.contains('is-open')) { setOpen(false); navToggle.focus(); }
  });
  matchMedia('(min-width: 768px)').addEventListener('change', (e) => { if (e.matches) setOpen(false); });
}
```

## 3. Hero variants

**Split hero** (text left, CSS-only product mockup right; stacks on mobile):
```html
<section class="hero glow" id="top">
  <div class="container split">
    <div class="stack stack-lg">
      <p class="eyebrow">Invoicing for studios</p>
      <h1>Get paid in 3 days, not 30.</h1>
      <p class="lead">Mintline sends the invoice, chases late clients and reconciles your bank feed, so a 4-person studio saves about 6 hours a month.</p>
      <div class="cluster">
        <a class="btn btn-primary btn-lg" href="#signup">Start 14-day trial</a>
        <a class="btn btn-ghost btn-lg" href="#how">See how it works</a>
      </div>
      <p class="muted text-sm">No card required · Cancel anytime</p>
    </div>
    <div class="mockup" aria-hidden="true">
      <div class="mockup__bar"><span></span><span></span><span></span></div>
      <div class="mockup__body">
        <div class="mockup__stat"><b>₩12,480,000</b><small>Paid this month</small></div>
        <div class="mockup__rows"><i></i><i></i><i></i><i></i></div>
      </div>
    </div>
  </div>
</section>
```
```css
.hero { padding-block: clamp(3.5rem, 2rem + 6vw, 7rem); }
.hero h1 { max-width: 14ch; }
:lang(ko) .hero h1 { max-width: 18ch; }
.mockup { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); overflow: hidden; }
.mockup__bar { display: flex; gap: 6px; padding: 12px 14px; background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.mockup__bar span { width: 10px; height: 10px; border-radius: 50%; background: var(--color-border-strong); opacity: .5; }
.mockup__body { display: grid; gap: var(--space-5); padding: var(--space-6); }
.mockup__stat b { display: block; font-size: var(--step-3); letter-spacing: -0.02em; }
.mockup__stat small { color: var(--color-text-muted); }
.mockup__rows { display: grid; gap: 10px; }
.mockup__rows i { display: block; height: 14px; border-radius: 7px; background: var(--color-surface-2); }
.mockup__rows i:nth-child(even) { width: 70%; }
.mockup__rows i:nth-child(3) { background: color-mix(in srgb, var(--color-primary) 35%, var(--color-surface-2)); }
```
**Centered hero**: same content in `container--narrow center stack stack-lg`, `.cluster { justify-content: center; }`, h1 ≤ 3 lines, a wide mockup below.
**Photo hero** (only if required): overlay `linear-gradient(rgb(0 0 0 / .55), rgb(0 0 0 / .35))` on the image so white text stays ≥ 4.5:1; set a solid `background-color` fallback.

## 4. Cards

```html
<ul class="grid-auto" role="list">
  <li class="feature card">
    <span class="feature__icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 8v4l3 2"/><circle cx="12" cy="12" r="9"/></svg></span>
    <h3><a href="#reminders">Automatic reminders</a></h3>
    <p>Polite follow-ups go out 3, 7 and 14 days after the due date. Clients pay 2.4× faster.</p>
  </li>
</ul>
```
```css
.feature { position: relative; display: grid; gap: var(--space-3); align-content: start;
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease), border-color var(--dur) var(--ease); }
.feature__icon { display: inline-grid; place-items: center; width: 44px; height: 44px; border-radius: var(--radius);
  color: var(--color-primary); background: color-mix(in srgb, var(--color-primary) 12%, var(--color-bg)); }
.feature h3 { font-size: var(--step-1); }
.feature h3 a { color: inherit; text-decoration: none; }
.feature h3 a::after { content: ""; position: absolute; inset: 0; border-radius: inherit; } /* whole card clickable */
.feature p { color: var(--color-text-muted); }
.feature:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--color-border-strong); }
.feature:has(a:focus-visible) { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.feature a:focus-visible { outline: none; } /* ring is drawn on the card instead */
```
Add the link + `::after` only if the card really links somewhere; otherwise drop the `<a>` and hover lift.

## 5. Pricing table

```html
<div class="pricing">
  <article class="plan card">
    <h3>Solo</h3>
    <p class="plan__price"><span>$12</span>/month</p>
    <p class="muted">For freelancers sending up to 20 invoices.</p>
    <ul class="checks" role="list"><li>20 invoices / month</li><li>Card + bank transfer</li><li>Email reminders</li></ul>
    <a class="btn btn-secondary" href="#signup">Choose Solo</a>
  </article>
  <article class="plan plan--featured card">
    <p class="plan__badge">Most popular</p>
    <h3>Studio</h3>
    <p class="plan__price"><span>$29</span>/month</p>
    <p class="muted">For teams of 2–10 with recurring clients.</p>
    <ul class="checks" role="list"><li>Unlimited invoices</li><li>Recurring billing</li><li>Bank reconciliation</li><li>3 team seats</li></ul>
    <a class="btn btn-primary" href="#signup">Choose Studio</a>
  </article>
  <!-- third plan: same structure, secondary button -->
</div>
```
```css
.pricing { display: grid; gap: var(--space-5); align-items: stretch; }
@media (min-width: 900px) { .pricing { grid-template-columns: repeat(3, 1fr); } }
.plan { position: relative; display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-6); }
.plan .btn { margin-top: auto; } /* buttons align at the bottom */
.plan--featured { border: 2px solid var(--color-primary); box-shadow: var(--shadow-lg); }
.plan__badge { position: absolute; top: 0; left: 50%; transform: translate(-50%, -50%);
  padding: 0.25rem 0.75rem; border-radius: var(--radius-pill); font-size: var(--step--1); font-weight: 600;
  background: var(--color-primary); color: var(--color-on-primary); white-space: nowrap; }
.plan__price { color: var(--color-text-muted); }
.plan__price span { font-size: var(--step-5); font-weight: 700; color: var(--color-text); letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.checks { display: grid; gap: var(--space-2); }
.checks li { display: flex; gap: var(--space-2); }
.checks li::before { content: ""; flex: none; width: 1.25rem; height: 1.25rem; margin-top: 0.15em; background: var(--color-primary);
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5'%3E%3Cpath d='M5 12l5 5L20 7'/%3E%3C/svg%3E") center / contain no-repeat; }
```
Korean prices: `₩29,000<small>/월</small>` or `29,000원/월`; show VAT note ("부가세 별도") in muted text.

## 6. Testimonial

```html
<figure class="quote">
  <blockquote><p>“We used to chase 15 overdue invoices every month. Now it's two, and Mintline handles them.”</p></blockquote>
  <figcaption>
    <span class="avatar" aria-hidden="true">JL</span>
    <span><strong>Jiyoon Lee</strong><br><span class="muted">Founder, Northfold Studio</span></span>
  </figcaption>
</figure>
```
```css
.quote { display: grid; gap: var(--space-5); max-width: 44rem; }
.quote blockquote p { font-size: var(--step-2); line-height: 1.4; font-weight: 500; letter-spacing: -0.01em; }
.quote figcaption { display: flex; align-items: center; gap: var(--space-3); }
.avatar { display: inline-grid; place-items: center; width: 48px; height: 48px; border-radius: 50%;
  font-weight: 700; background: color-mix(in srgb, var(--color-accent) 18%, var(--color-bg)); color: var(--color-text); }
```
Initials never break; use photos only if provided.

## 7. FAQ accordion (native, no JS)

```html
<div class="faq">
  <details name="faq" open>
    <summary>Can I import invoices from Excel?</summary>
    <p>Yes. Upload a .xlsx or .csv file and match the columns once; we keep the mapping for next time.</p>
  </details>
  <details name="faq">
    <summary>What happens when the trial ends?</summary>
    <p>Your account switches to read-only. Nothing is deleted, and you can upgrade any time.</p>
  </details>
</div>
```
```css
.faq { border-top: 1px solid var(--color-border); max-width: 48rem; }
.faq details { border-bottom: 1px solid var(--color-border); }
.faq summary {
  display: flex; justify-content: space-between; align-items: center; gap: var(--space-4);
  min-height: 44px; padding-block: var(--space-4); cursor: pointer; font-weight: 600; list-style: none;
}
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after {
  content: ""; flex: none; width: 10px; height: 10px; margin-right: 4px;
  border-right: 2px solid currentColor; border-bottom: 2px solid currentColor;
  transform: rotate(45deg); transition: transform var(--dur) var(--ease);
}
.faq details[open] summary::after { transform: rotate(-135deg); }
.faq details p { padding-bottom: var(--space-4); color: var(--color-text-muted); }
```
`name="faq"` = only one open at a time (older browsers ignore it).

## 8. Form with validation states

```html
<form class="form" id="contact-form" novalidate>
  <div class="field">
    <label for="f-name">Name</label>
    <input id="f-name" name="name" type="text" autocomplete="name" required aria-describedby="f-name-error">
    <p class="error" id="f-name-error" hidden>Please enter your name.</p>
  </div>
  <div class="field">
    <label for="f-email">Work email</label>
    <input id="f-email" name="email" type="email" autocomplete="email" required aria-describedby="f-email-hint f-email-error">
    <p class="hint" id="f-email-hint">We reply within one business day.</p>
    <p class="error" id="f-email-error" hidden>Enter an email like name@company.com.</p>
  </div>
  <div class="field">
    <label for="f-msg">Message <span class="muted">(optional)</span></label>
    <textarea id="f-msg" name="message" rows="4"></textarea>
  </div>
  <button class="btn btn-primary" type="submit">Send message</button>
  <p class="form-status" role="status" aria-live="polite"></p>
</form>
```
```css
.form { display: grid; gap: var(--space-5); max-width: 32rem; }
.field { display: grid; gap: var(--space-2); }
.field label { font-weight: 600; font-size: 0.9375rem; }
.field input, .field select, .field textarea {
  width: 100%; min-height: 44px; padding: 0.625rem 0.875rem; font-size: 1rem;
  color: var(--color-text); background: var(--color-bg);
  border: 1px solid var(--color-border-strong); border-radius: var(--radius);
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}
.field input:focus-visible, .field textarea:focus-visible, .field select:focus-visible {
  outline: 2px solid transparent; border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 35%, transparent);
}
.field [aria-invalid="true"], .field :user-invalid { border-color: var(--color-danger); }
.hint { font-size: var(--step--1); color: var(--color-text-muted); }
.error { font-size: var(--step--1); color: var(--color-danger); font-weight: 500; }
.error::before { content: "⚠ "; }
.form-status:empty { display: none; }
.form-status { padding: var(--space-3) var(--space-4); border-radius: var(--radius);
  background: color-mix(in srgb, var(--color-success) 12%, var(--color-bg)); color: var(--color-text); }
```
```js
const form = document.getElementById('contact-form');
if (form) {
  const validate = (field) => {
    const error = document.getElementById(field.id + '-error');
    const ok = field.checkValidity();
    field.setAttribute('aria-invalid', String(!ok));
    if (error) error.hidden = ok;
    return ok;
  };
  form.addEventListener('input', (e) => {
    if (e.target.getAttribute('aria-invalid') === 'true') validate(e.target);
  });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const fields = [...form.querySelectorAll('input, textarea, select')];
    const invalid = fields.filter((f) => !validate(f));
    const status = form.querySelector('.form-status');
    if (invalid.length) { invalid[0].focus(); return; }
    if (status) status.textContent = 'Thanks! Your message was sent. We will reply within one business day.';
    form.reset();
    fields.forEach((f) => f.removeAttribute('aria-invalid'));
  });
}
```
No backend exists: show the success message; never post to a made-up URL.

## 9. Footer

```html
<footer class="site-footer">
  <div class="container footer-grid">
    <div class="stack"><a class="brand" href="#top">Mintline</a><p class="muted">Invoicing for small studios. Seoul · Berlin.</p></div>
    <nav aria-label="Product"><h2 class="footer-h">Product</h2><ul role="list"><li><a href="#features">Features</a></li><li><a href="#pricing">Pricing</a></li></ul></nav>
    <nav aria-label="Company"><h2 class="footer-h">Company</h2><ul role="list"><li><a href="#about">About</a></li><li><a href="mailto:hello@mintline.app">hello@mintline.app</a></li></ul></nav>
  </div>
  <div class="container footer-bottom"><p class="muted">© <span id="year">2026</span> Mintline Inc.</p></div>
</footer>
```
```css
.site-footer { padding-block: var(--space-8) var(--space-6); background: var(--color-surface); border-top: 1px solid var(--color-border); }
.footer-grid { display: grid; gap: var(--space-6); grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr)); }
.footer-h { font-size: var(--step--1); text-transform: uppercase; letter-spacing: .08em; color: var(--color-text-muted); margin-bottom: var(--space-3); }
.site-footer ul { display: grid; gap: var(--space-2); }
.site-footer a:not(.brand) { color: var(--color-text); text-decoration: none; }
.site-footer a:not(.brand):hover { color: var(--color-primary); text-decoration: underline; }
.footer-bottom { margin-top: var(--space-7); padding-top: var(--space-5); border-top: 1px solid var(--color-border); }
```
```js
const year = document.getElementById('year'); if (year) year.textContent = new Date().getFullYear();
```

## 10. Modal with `<dialog>`

```html
<button class="btn btn-secondary" type="button" data-open-dialog="demo-dialog">Watch 2-min demo</button>
<dialog class="modal" id="demo-dialog" aria-labelledby="demo-title">
  <div class="modal__body">
    <div class="modal__head">
      <h2 id="demo-title">Book a 20-minute demo</h2>
      <button class="icon-btn" type="button" data-close-dialog aria-label="Close">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
    <p class="muted">Pick a time and we will walk through your real invoices.</p>
    <div class="cluster"><button class="btn btn-secondary" type="button" data-close-dialog>Not now</button><a class="btn btn-primary" href="#signup">Choose a time</a></div>
  </div>
</dialog>
```
```css
.modal { width: min(100% - 2rem, 32rem); padding: 0; border: 0; border-radius: var(--radius-lg);
  background: var(--color-bg); color: var(--color-text); box-shadow: var(--shadow-lg); }
.modal::backdrop { background: rgb(0 0 0 / 0.5); }
.modal[open] { animation: modal-in var(--dur) var(--ease); }
@keyframes modal-in { from { opacity: 0; transform: translateY(8px) scale(.98); } }
.modal__body { display: grid; gap: var(--space-4); padding: var(--space-6); }
.modal__head { display: flex; justify-content: space-between; align-items: start; gap: var(--space-4); }
.modal__head h2 { font-size: var(--step-2); }
body:has(.modal[open]) { overflow: hidden; }
```
```js
document.querySelectorAll('[data-open-dialog]').forEach((btn) => {
  const dlg = document.getElementById(btn.dataset.openDialog);
  if (dlg) btn.addEventListener('click', () => dlg.showModal());
});
document.querySelectorAll('dialog.modal').forEach((dlg) => {
  dlg.addEventListener('click', (e) => {
    if (e.target === dlg || e.target.closest('[data-close-dialog]')) dlg.close(); // backdrop or close button
  });
});
```
`showModal()` traps focus, closes on Escape and returns focus to the opener natively. Never build modals from `<div>` overlays.

## 11. Tabs

```html
<div class="tabs">
  <div class="tabs__list" role="tablist" aria-label="Plans">
    <button role="tab" id="tab-monthly" aria-selected="true" aria-controls="panel-monthly" type="button">Monthly</button>
    <button role="tab" id="tab-yearly" aria-selected="false" aria-controls="panel-yearly" tabindex="-1" type="button">Yearly (−20%)</button>
  </div>
  <div role="tabpanel" id="panel-monthly" aria-labelledby="tab-monthly" tabindex="0"><p>Billed every month. Switch plans anytime.</p></div>
  <div role="tabpanel" id="panel-yearly" aria-labelledby="tab-yearly" tabindex="0" hidden><p>Billed once a year. Two months free.</p></div>
</div>
```
```css
.tabs__list { display: inline-flex; gap: var(--space-1); padding: var(--space-1); background: var(--color-surface); border-radius: var(--radius-pill); }
.tabs__list [role="tab"] { min-height: 44px; padding: 0.5rem 1rem; border: 0; border-radius: var(--radius-pill);
  background: transparent; color: var(--color-text-muted); font-weight: 600; }
.tabs__list [role="tab"][aria-selected="true"] { background: var(--color-bg); color: var(--color-text); box-shadow: var(--shadow-sm); }
[role="tabpanel"] { padding-top: var(--space-5); }
```
```js
document.querySelectorAll('[role="tablist"]').forEach((list) => {
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const select = (tab) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute('aria-controls'));
      if (panel) panel.hidden = !on;
    });
    tab.focus();
  };
  list.addEventListener('click', (e) => { const t = e.target.closest('[role="tab"]'); if (t) select(t); });
  list.addEventListener('keydown', (e) => {
    const i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    select(tabs[(next + tabs.length) % tabs.length]);
  });
});
```
Use tabs only for 2–6 short, parallel panels.
