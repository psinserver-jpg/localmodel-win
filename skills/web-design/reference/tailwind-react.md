---
name: tailwind-react
description: Tailwind CSS via CDN for prototypes, class conventions, React component structure with Vite, state handling and common mistakes.
triggers: [tailwind, tailwindcss, react, jsx, tsx, vite, next.js, nextjs, component library, shadcn, useState, useEffect, 리액트, 테일윈드, 컴포넌트]
---
# Tailwind CSS & React

Use these ONLY when the user asks for Tailwind or React (or the existing project uses them). Otherwise plain HTML/CSS is simpler and safer.

## 1. Tailwind via CDN (single-file prototypes)

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>페이지 제목</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'media',
      theme: { extend: {
        colors: { brand: { 50:'#eff6ff', 500:'#3b82f6', 600:'#2563eb', 700:'#1d4ed8' } },
        fontFamily: { sans: ['Pretendard', 'system-ui', 'sans-serif'] },
      } },
    };
  </script>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
</head>
<body class="bg-white text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
  ...
</body>
</html>
```

- The CDN script is for prototypes; for production use the Vite plugin (below).
- `tailwind.config` must be set in a `<script>` AFTER the CDN script.
- Only use classes that exist. Arbitrary values use brackets: `w-[42rem]`, `bg-[#0f172a]`.

### Class conventions
- Order: layout → box → typography → color → state: `flex items-center gap-3 px-4 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 rounded-lg`.
- Container: `mx-auto max-w-6xl px-4 sm:px-6 lg:px-8`.
- Section spacing: `py-16 sm:py-24`.
- Responsive prefixes are min-width: `sm:` 640, `md:` 768, `lg:` 1024, `xl:` 1280. Base classes = mobile.
- Grid: `grid gap-6 sm:grid-cols-2 lg:grid-cols-3`.
- Text: `text-4xl sm:text-5xl font-bold tracking-tight`, body `text-base leading-7 text-slate-600 dark:text-slate-300`.
- Korean text: add `break-keep` (word-break: keep-all).
- Focus: always add `focus-visible:` styles to interactive elements.
- Don't repeat 20 classes on 10 identical buttons in plain HTML — in React make a component; in plain HTML accept it, but keep them identical.

### Button & card recipes
```html
<a href="#contact" class="inline-flex items-center justify-center min-h-11 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600">문의하기</a>

<article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
  <h3 class="text-lg font-semibold">제목</h3>
  <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">설명 문장.</p>
</article>
```

## 2. React project setup (Vite)

```bash
npm create vite@latest my-app -- --template react      # or react-ts
cd my-app
npm install
npm run dev        # http://localhost:5173
npm run build      # outputs dist/
```

Tailwind v4 with Vite:
```bash
npm install tailwindcss @tailwindcss/vite
```
```js
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({ plugins: [react(), tailwindcss()] });
```
```css
/* src/index.css */
@import "tailwindcss";
```

### File structure
```
src/
  main.jsx          // createRoot(...).render(<App />)
  App.jsx           // page composition only
  components/       // Button.jsx, Navbar.jsx, Hero.jsx, ...
  data/             // content arrays (menu items, features)
  index.css
```

### Component rules
- One component per file, PascalCase name, `export default function Navbar() {}`.
- Content as data arrays, rendered with `.map()` and a stable `key` (an id, not the index if items can reorder).
- Props destructured: `function Card({ title, children }) {}`.
- `className`, not `class`; `htmlFor`, not `for`; self-close `<img />`, `<input />`.
- Event handlers: `onClick={() => setOpen(o => !o)}` — never `onClick={setOpen(true)}` (calls immediately).
- State: `const [open, setOpen] = useState(false);` Updates based on previous value use the function form.
- Effects only for syncing with outside systems (timers, fetch, listeners). Always return a cleanup:

```jsx
useEffect(() => {
  const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
  window.addEventListener('keydown', onKey);
  return () => window.removeEventListener('keydown', onKey);
}, []);
```

- Fetching data:

```jsx
const [items, setItems] = useState([]);
const [status, setStatus] = useState('loading'); // 'loading' | 'ok' | 'error'
useEffect(() => {
  let alive = true;
  fetch('/api/items')
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(d => { if (alive) { setItems(d); setStatus('ok'); } })
    .catch(() => alive && setStatus('error'));
  return () => { alive = false; };
}, []);
```
  Always render loading, error and empty states.

- Forms: controlled inputs (`value` + `onChange`), `e.preventDefault()` in `onSubmit`.
- Images in `public/` are referenced as `/logo.svg`; imported assets via `import logo from './assets/logo.svg'`.

## 3. Common mistakes to avoid

- Mixing `class` and `className`, or forgetting to import `useState` / `useEffect` from `react`.
- Missing `key` in lists; using `Math.random()` as key.
- Mutating state (`items.push(x)`) instead of `setItems([...items, x])`.
- Infinite loop: setting state inside an effect without a dependency array.
- Rendering objects directly (`{user}`) instead of fields (`{user.name}`).
- Tailwind classes built dynamically (`bg-${color}-500`) are not generated — use full class names in a lookup object.
- Using Next.js-only APIs (`next/image`, `getServerSideProps`) in a Vite app.
- Telling the user to open `index.html` of a Vite project directly — it must be run with `npm run dev` or built.
- Forgetting run instructions: always give `npm install` and `npm run dev`.
