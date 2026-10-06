---
name: page-recipes
description: Section-by-section blueprints and copywriting rules for landing pages, SaaS, portfolios, restaurants and local businesses, blogs, e-commerce product pages and dashboards.
triggers: [landing page, saas, startup, product page, portfolio, resume, personal site, restaurant, cafe, bakery, salon, clinic, local business, blog, article, magazine, e-commerce, shop, store, product detail, dashboard, admin, analytics, copywriting, copy, 랜딩페이지, 포트폴리오, 카페, 식당, 레스토랑, 쇼핑몰, 상세페이지, 블로그, 대시보드, 관리자, 회사 소개, 이력서, 카피]
---
# Page Recipes

Pick the recipe closest to the request, then adapt. Each recipe lists sections top to bottom with their purpose and layout. Use 5–9 sections for a marketing page; fewer, stronger sections beat many weak ones. Alternate section backgrounds (`bg` / `surface`) and layouts (split / grid / single column).

## Copywriting rules (all pages)
- Write all visible copy in the user's language. Invent a plausible business if none is given (name, city, numbers) and keep it consistent across the page.
- Headline = outcome + specificity: "Get paid in 3 days, not 30", "Seoul's slow-fermented sourdough, baked at 6 a.m." Not "Welcome to our website".
- Subheadline (1–2 sentences): who it is for + how it works + one proof number.
- CTA labels = verb + object: "Start free trial", "Book a table", "View projects", "Add to cart". Never "Click here" or "Submit".
- Benefits over features: "Close the month in 1 day" beats "Automated reconciliation engine".
- Proof is specific: "4.8/5 from 1,240 reviews", "Used by 312 studios in 14 countries", a named quote with role and company.
- Short paragraphs: 1–3 sentences. Feature descriptions 12–25 words.
- Korean copy: use one register throughout (polite `-요` / `-니다` for business; `-하세요` CTAs like "무료로 시작하기", "예약하기", "장바구니 담기"). Avoid translated-sounding phrases ("당신의 잠재력을 열어보세요"). Use real Korean formats: `02-1234-5678`, `₩29,000` or `29,000원`, `서울 마포구 ○○로 12`, dates `2026년 3월 14일`.

## 1. Product / generic landing page
1. **Header**: logo, 3–5 anchor links, one primary CTA. Sticky.
2. **Hero**: eyebrow, h1 (≤ 10 words), subheadline, primary + ghost CTA, risk-reducer line ("No card required"). Visual: CSS mockup or SVG illustration. Split layout ≥ 900px.
3. **Social proof strip**: "Trusted by teams at" + 4–6 text wordmarks in muted color (styled text, not fake logos), or 3 key stats.
4. **Problem → solution**: short split section naming the pain in the reader's words, then how the product fixes it.
5. **Features**: 3–6 items. Use a bento grid or alternating split rows (image left/right) for the top 2–3, a compact list for the rest. Not 9 identical cards.
6. **How it works**: 3 numbered steps in a row (stack on mobile), each with a verb title ("Connect your bank").
7. **Testimonials**: 1 large quote, or 3 quotes in a grid. Name, role, company.
8. **Pricing** (if relevant): 3 tiers, middle featured, monthly/yearly tabs optional.
9. **FAQ**: 4–6 real objections (price, security, cancel, migration, support hours).
10. **Final CTA band**: primary-colored or dark band, h2 restating the outcome, one button.
11. **Footer**: brand blurb, 2–4 link groups, contact, © year.

## 2. SaaS / app marketing site
Same as landing page, plus:
- Hero visual = product UI mockup (CSS "browser window" with fake stats, table rows, a small chart drawn with inline SVG `<polyline>` or CSS bars).
- **Integrations** row: names in pill tags ("Slack", "Notion", "Google Sheets").
- **Security / trust** block for B2B: SOC 2, GDPR, data region, uptime "99.95% uptime over the last 12 months".
- **Comparison table** (optional): your product vs. "spreadsheets" / "agencies", 5–7 rows, check marks with text for screen readers.
- Pricing shows the per-seat logic and a "Contact sales" enterprise tier.
Tone: confident, concrete, technical where the audience is technical. Accent sparingly on numbers and CTAs.

## 3. Portfolio (designer, developer, photographer)
1. **Header**: name as logo, links: Work, About, Contact.
2. **Intro hero**: 1 bold statement in large type (`--step-6`), e.g. "I design booking flows that people finish." + role, city, availability ("Available for freelance from May").
3. **Selected work**: 3–6 case studies. Large cards (2 columns ≥ 768px, 1 on mobile), each: visual (gradient/SVG cover with project initials, or provided image), project name, one-line outcome ("Cut checkout drop-off by 18%"), tags (role, year). Link to an in-page case-study section or `<dialog>`.
4. **Case study** (per project or one featured): Problem → Process (3 steps) → Result with numbers → What I'd do differently.
5. **About**: short bio (60–100 words), skills as grouped lists (Design / Code / Tools), photo slot or illustrated avatar.
6. **Experience / clients**: timeline list (year, company, role) using `<ol>`.
7. **Contact**: big email link (`mailto:`), social links with icons + text labels.
Design: personality matters most here. Choose one bold move: oversized type, a monochrome palette with one vivid accent, an editorial grid, or one playful hover micro-interaction. Keep the work as the hero; UI chrome stays quiet.
Developer portfolios: show code-adjacent signals (GitHub-style project cards with language dot, stars, short description), monospace accents only for labels.

## 4. Restaurant / cafe / local business
Visitors want: what you serve, where, when open, how to book or call. Put those within the first screen and repeat in the footer.
1. **Header**: name, Menu, Visit, Book links, `tel:` call button on mobile.
2. **Hero**: atmosphere headline, 1-line description, CTAs "Book a table" + "View menu". Quick facts row: hours today, neighborhood, price range.
3. **About / story**: 2 short paragraphs + signature dish highlight.
4. **Menu**: grouped by category with `<h3>`s; each item = name, short description, price aligned right with dotted leader or flex gap. Mark vegetarian/spicy with text badges. 4–8 items per group.
5. **Gallery** (optional): CSS-gradient tiles or provided photos in a 3-column grid with captions.
6. **Reviews**: 2–3 quotes with source ("Naver 4.7 · 812 reviews").
7. **Visit**: address, opening hours as a `<table>` or `<dl>` (Mon–Fri 11:30–21:30, break time 15:00–17:00, closed Mondays), parking, nearest station. Map: a styled address card with a link to the map service (`https://map.naver.com/p/search/<query>` or `https://www.google.com/maps/search/?api=1&query=<query>`), not a broken iframe.
8. **Booking / contact**: phone link, reservation form (date, time, party size) or link to the booking service.
9. **Footer**: hours, address, phone, social, business registration info for Korea (상호, 대표, 사업자등록번호).
Tone: warm, sensory, short. Palette: warm neutrals (Espresso, Forest palettes) or a deep brand color; serif or rounded headings.

## 5. Blog / article / magazine
- **Index page**: header with publication name; featured post (large split card); grid of post cards (title, 1–2 line excerpt, date `<time datetime>`, reading time, category tag); category filter links; newsletter signup.
- **Article page** structure:
  ```html
  <main id="main">
    <article class="container--narrow prose">
      <header>
        <p class="eyebrow">Design</p>
        <h1>Why your checkout loses 1 in 5 buyers</h1>
        <p class="lead">Five fixes we tested on 40 stores, with numbers.</p>
        <p class="muted"><span>By Minji Park</span> · <time datetime="2026-03-14">March 14, 2026</time> · 7 min read</p>
      </header>
      <!-- h2/h3 sections, figures, blockquotes, code, lists -->
    </article>
  </main>
  ```
- Prose styles: body `1.0625–1.125rem`, line-height 1.7 (Korean 1.8), `max-width: 68ch`, paragraph spacing `1.25em`, h2 margin-top `2.5em`, `figure` with `figcaption` in muted small text, blockquote with 3px left border in primary, `pre` scrollable.
  ```css
  .prose > * + * { margin-top: 1.25em; }
  .prose h2 { margin-top: 2.5em; font-size: var(--step-3); }
  .prose h3 { margin-top: 2em; font-size: var(--step-2); }
  .prose blockquote { padding-left: var(--space-5); border-left: 3px solid var(--color-primary); color: var(--color-text-muted); }
  .prose img, .prose pre { border-radius: var(--radius); }
  ```
- Optional: table of contents (sticky aside ≥ 1024px), author box, related posts (3 cards), "Back to top" link.
- Typography is the design: choose a good serif or a refined sans, generous whitespace, almost no decoration.

## 6. E-commerce product page
1. **Header**: logo, category nav, search, cart button with item count (`aria-label="Cart, 2 items"`).
2. **Breadcrumb**: `<nav aria-label="Breadcrumb"><ol>` Home / Bags / Totes.
3. **Product main** (split ≥ 900px): left gallery (main image + 4 thumbnail buttons that swap the main image, `aria-pressed` on the active thumb); right: name (h1), rating summary ("4.7 ★ · 326 reviews" link to reviews), price (sale price + struck-through original in `<s>` with visually-hidden "Original price"), short description, options (color swatches as radio inputs with labels; size as radio pills), quantity stepper (`<button>` − / `<input type="number" min="1">` / +), primary "Add to cart" full-width on mobile, secondary "Save", delivery info ("Free shipping over ₩50,000 · Ships in 1–2 days"), returns line.
4. **Details**: `<details>` groups for Materials, Size & fit, Care, Shipping & returns.
5. **Reviews**: rating distribution bars (CSS widths), 3–5 reviews with name, date, verified badge, text.
6. **Related products**: 4 product cards (image, name, price, rating), horizontal scroll on mobile with `scroll-snap-type: x mandatory` or 2-column grid.
7. **Sticky mobile buy bar** (optional, < 768px): price + Add to cart, `position: sticky; bottom: 0`.
Rules: price and the primary button are the most prominent items after the product image. Use real-looking SKUs, materials, dimensions ("38 × 32 × 12 cm, 480 g"). Cart interaction in vanilla JS updates the count and shows a toast with `role="status"`.

## 7. Dashboard / admin layout
Structure: sidebar navigation + top bar + content grid. Dense but calm: smaller type (14–15px for tables), more surfaces, fewer colors.
```html
<div class="app">
  <aside class="app-sidebar"><nav aria-label="Main"><!-- logo + nav links with icons + text --></nav></aside>
  <header class="app-topbar"><!-- page title, search, user menu --></header>
  <main class="app-main" id="main"><!-- KPI cards, charts, tables --></main>
</div>
```
```css
.app { display: grid; min-height: 100svh; grid-template-columns: 1fr; grid-template-rows: auto 1fr; grid-template-areas: "top" "main"; }
.app-sidebar { display: none; }
.app-topbar { grid-area: top; display: flex; align-items: center; justify-content: space-between; gap: var(--space-4);
  padding: var(--space-3) var(--space-5); border-bottom: 1px solid var(--color-border); background: var(--color-bg); }
.app-main { grid-area: main; padding: var(--space-5); background: var(--color-surface); display: grid; gap: var(--space-5); align-content: start; min-width: 0; }
@media (min-width: 1024px) {
  .app { grid-template-columns: 16rem 1fr; grid-template-areas: "side top" "side main"; }
  .app-sidebar { grid-area: side; display: block; position: sticky; top: 0; height: 100svh; overflow-y: auto;
    padding: var(--space-5) var(--space-4); border-right: 1px solid var(--color-border); background: var(--color-bg); }
}
.kpis { display: grid; gap: var(--space-4); grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr)); }
.kpi { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-5); }
.kpi__value { font-size: var(--step-3); font-weight: 700; font-variant-numeric: tabular-nums; }
.kpi__delta--up { color: var(--color-success); } .kpi__delta--down { color: var(--color-danger); }
```
- Below 1024px the sidebar becomes a menu toggled from the top bar (same pattern as the navbar toggle).
- KPI row: 4 cards (label, value, delta with ▲/▼ AND text "+12.4% vs last month", not color alone).
- Charts: inline SVG (bars with `<rect>`, lines with `<polyline>`), with a visible title and an accessible summary (`<title>` / `aria-label`), axis labels in muted 12–13px text. Use one hue + neutrals; a second hue only for comparison.
- Tables: in `.table-wrap`, sticky header, right-aligned numbers with `tabular-nums`, status as text badges, row hover `--color-surface-2`, actions as icon buttons with `aria-label`.
- Use realistic data: 8–12 rows, plausible names, dates in the last 30 days, amounts that add up to the KPI totals.
- Active nav item: `aria-current="page"`, primary-tinted background, never only color change on text.

## 8. Other quick recipes
- **Company / corporate (회사 소개)**: hero with mission, numbers band (founded, employees, offices), services grid, clients wordmarks, team cards (3–4 leaders), history timeline, careers CTA, contact with address/phone/email.
- **Event / conference**: date + city in hero with "Get tickets", speakers grid (initial avatars), schedule as tabs per day with `<time>`, venue, ticket tiers, sponsors, FAQ.
- **Clinic / academy / salon**: services with prices or durations, staff profiles, booking CTA repeated, opening hours, location, reviews, insurance or certificate notes.
- **App download page**: hero with CSS phone mockup, 3 key screens, store badges as styled buttons with text, ratings, FAQ.
- **Coming soon / waitlist**: single screen, h1, one-sentence value, email form with success state, launch date, social links.

## Final pass for every page
- One clear primary CTA repeated in hero, mid-page and final band; same label each time.
- Every nav anchor scrolls to a real section `id`.
- Numbers, names and prices are consistent across sections.
- Mobile check: hero text first, buttons full-width or wrapping, no tiny tap targets, tables scroll.
