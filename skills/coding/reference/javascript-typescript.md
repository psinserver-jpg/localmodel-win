---
name: javascript-typescript
description: Modern JavaScript (ES2022+) and TypeScript for Node and browsers, ESM vs CommonJS, project setup, fetch, async error handling, tsconfig and a minimal Express server.
triggers: [javascript, typescript, js, node, nodejs, npm, npx, express, react, vue, svelte, nextjs, vite, esm, commonjs, package.json, tsconfig, fetch, promise, async, await, 자바스크립트, 타입스크립트, 노드, 리액트]
---
# JavaScript and TypeScript Reference

Target Node 20 or newer (LTS) and evergreen browsers. Write modern JavaScript only.

## Modern syntax (ES2022+)

- `const` by default, `let` when reassigned, never `var`.
- Strict equality only: `===` and `!==`.
- Optional chaining and nullish coalescing: `user?.address?.city ?? "unknown"`. `??` keeps `0` and `""`; `||` does not.
- Destructuring with defaults: `const { port = 3000, host = "127.0.0.1" } = options;`
- Template literals: `` `Hello ${name}` ``.
- Spread to copy: `const next = { ...state, count: state.count + 1 };` and `[...items, newItem]`.
- Arrays: `map`, `filter`, `find`, `some`, `every`, `reduce`, `includes`, `at(-1)`, `flatMap`. `Object.entries(obj)` / `Object.fromEntries(pairs)`.
- `structuredClone(value)` for deep copy. `crypto.randomUUID()` for IDs (Node 19+ global, browsers).
- Classes with private fields: `#count = 0;`.
- `for...of` for arrays, never `for...in` on arrays.
- Numbers: `Number.parseInt(s, 10)`, `Number(s)`, check `Number.isNaN(n)`. Numeric sort needs a comparator: `nums.sort((a, b) => a - b)`.
- `toSorted()`, `toReversed()` return new arrays (Node 20+); `sort()` mutates.

## ESM vs CommonJS

Pick ONE module system per project. Prefer ESM for new projects.

ESM (`"type": "module"` in `package.json`, or `.mjs` files):

```js
// math.js
export function add(a, b) {
  return a + b;
}
export default function multiply(a, b) {
  return a * b;
}

// main.js
import multiply, { add } from './math.js'; // the .js extension is REQUIRED in Node ESM
import { readFile } from 'node:fs/promises';
import path from 'node:path';

console.log(add(2, 3), multiply(2, 3));
```

CommonJS (no `"type"` field, or `.cjs` files):

```js
// math.cjs
function add(a, b) {
  return a + b;
}
module.exports = { add };

// main.cjs
const { add } = require('./math.cjs');
console.log(add(2, 3));
```

Rules:
- Never mix `require` and `import` in the same file.
- Default export -> `import x from`; named export -> `import { x } from`. A mismatch gives `x is not a function` or `undefined`.
- ESM has no `__dirname` / `__filename`. Use `import.meta.dirname` (Node 20.11+) or:

```js
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dataFile = path.join(__dirname, 'data.json');
```

- Top-level `await` works only in ESM.
- Import JSON in ESM with `JSON.parse(await readFile(file, 'utf8'))` (works everywhere).

## Node project setup

```
mkdir my-app
cd my-app
npm init -y
npm pkg set type=module
npm install express
npm install --save-dev vitest
```

Resulting `package.json` (versions illustrative; use what `npm install` writes):

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "type": "module",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "test": "vitest run"
  },
  "dependencies": {
    "express": "^5.1.0"
  },
  "devDependencies": {
    "vitest": "^3.2.4"
  },
  "engines": {
    "node": ">=20"
  }
}
```

- Commit `package-lock.json`. Never commit `node_modules/`.
- `npm ci` installs exactly from the lockfile (CI, clean installs).
- Scripts must be cross-platform: no `rm -rf`, `cp`, `export VAR=x` inside scripts. Use `rimraf`, Node scripts, or `cross-env`.
- Env file: Node 20.6+ supports `node --env-file=.env src/index.js`. Read with `process.env.PORT ?? '3000'`.

## Files

```js
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

export async function loadJson(file, fallback) {
  try {
    return JSON.parse(await readFile(file, 'utf8'));
  } catch (err) {
    if (err.code === 'ENOENT') return fallback;
    throw err;
  }
}

export async function saveJson(file, data) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, JSON.stringify(data, null, 2), 'utf8');
}
```

## fetch and async error handling

`fetch` is global in Node 18+ and browsers. It does NOT throw on 404/500; check `res.ok`.

```js
export async function getJson(url, { timeoutMs = 10000 } = {}) {
  const res = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`GET ${url} failed: ${res.status} ${res.statusText} ${body.slice(0, 200)}`);
  }
  return res.json();
}

export async function postJson(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`POST ${url} failed: ${res.status}`);
  return res.json();
}
```

Async rules:
- Every `await` that can fail is inside `try/catch` at some level, or the caller handles the rejected promise.
- Parallel: `await Promise.all(items.map(fetchItem))`. Use `Promise.allSettled` when some may fail and you want the rest.
- Never `items.forEach(async (x) => { await ... })`; it does not wait. Use `for (const x of items) { await ... }` (sequential) or `Promise.all` (parallel).
- An `async` function always returns a Promise. Forgetting `await` gives you `Promise { <pending> }` instead of the value.
- In CLI scripts, set the exit code on failure:

```js
async function main() {
  const data = await getJson('https://api.github.com/repos/nodejs/node');
  console.log(data.full_name, data.stargazers_count);
}

main().catch((err) => {
  console.error(err.message);
  process.exitCode = 1;
});
```

## Express minimal server

```js
// src/index.js  (package.json has "type": "module"; npm install express)
import express from 'express';

const PORT = Number(process.env.PORT ?? 3000);
const app = express();
app.use(express.json());

const todos = []; // demo storage; use a database for real data
let nextId = 1;

app.get('/api/todos', (req, res) => {
  res.json(todos);
});

app.post('/api/todos', (req, res) => {
  const title = typeof req.body?.title === 'string' ? req.body.title.trim() : '';
  if (!title) {
    return res.status(400).json({ error: 'title is required' });
  }
  const todo = { id: nextId++, title, done: false };
  todos.push(todo);
  res.status(201).json(todo);
});

app.delete('/api/todos/:id', (req, res) => {
  const id = Number.parseInt(req.params.id, 10);
  const index = todos.findIndex((t) => t.id === id);
  if (index === -1) return res.status(404).json({ error: 'todo not found' });
  todos.splice(index, 1);
  res.status(204).end();
});

app.use((req, res) => {
  res.status(404).json({ error: 'not found' });
});

// Error handler: must have exactly 4 parameters to be treated as one.
app.use((err, req, res, next) => {
  const status = err.status ?? 500; // express.json() sets 400 for malformed JSON
  if (status >= 500) console.error(err);
  res.status(status).json({ error: status >= 500 ? 'internal server error' : err.message });
});

app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
```

- Route params and query values are always strings; convert them.
- In Express 4, errors thrown inside `async` handlers are NOT caught; wrap the body in `try/catch` and call `next(err)`. Express 5 forwards rejected promises automatically.
- Static files: `app.use(express.static('public'))`. CORS: `npm install cors`, then `app.use(cors({ origin: 'http://localhost:5173' }))`.

## TypeScript

Install and set up for Node:

```
npm install --save-dev typescript @types/node tsx
npx tsc --init
```

A good `tsconfig.json` for a Node ESM project:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "sourceMap": true,
    "types": ["node"]
  },
  "include": ["src"]
}
```

Scripts: `"dev": "tsx watch src/index.ts"`, `"build": "tsc"`, `"start": "node dist/index.js"`, `"typecheck": "tsc --noEmit"`.

- With `NodeNext`, relative imports in `.ts` files still use the `.js` extension: `import { add } from './math.js';`.
- Projects built by Vite or Next.js already have a tsconfig; do not replace it.

Typing basics:

```ts
export interface User {
  id: number;
  name: string;
  email?: string; // optional
}

export type Status = 'active' | 'disabled';

export function findUser(users: User[], id: number): User | undefined {
  return users.find((u) => u.id === id);
}

export function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as User).id === 'number' &&
    typeof (value as User).name === 'string'
  );
}

const config = { retries: 3, mode: 'fast' } as const;
const counts: Record<string, number> = {};
type UserPatch = Partial<Omit<User, 'id'>>;
```

- Use `unknown` for untrusted data (JSON, API responses) and narrow it; avoid `any`.
- Do not use `!` (non-null assertion) to silence errors; handle `undefined`.
- Validate external data at runtime too; types disappear after compiling. Use a type guard or a schema library like zod.
- `catch (err)` gives `unknown`: use `err instanceof Error ? err.message : String(err)`.

## Browser JavaScript

- Load scripts with `<script type="module" src="app.js"></script>` or `<script defer src="app.js"></script>` so the DOM exists when the code runs.
- Put user data into the page with `el.textContent = value`, never `innerHTML` with untrusted data.
- `document.querySelector` returns `null` when nothing matches; check before use.
- Use `addEventListener('submit', (e) => { e.preventDefault(); ... })` for forms.
- `localStorage` stores strings only: `JSON.stringify` on write, `JSON.parse` in `try/catch` on read.

## React essentials

- Function components and hooks only. Root: `createRoot(document.getElementById('root')).render(<App />)` from `react-dom/client`.
- Every list item needs a stable unique `key`: `items.map((item) => <li key={item.id}>{item.name}</li>)`. Do not use the array index if items can be reordered or deleted.
- Never mutate state: `setItems((prev) => [...prev, newItem])`, `setUser((prev) => ({ ...prev, name }))`.
- `useEffect` dependency array must list every value used inside. Return a cleanup function for timers and subscriptions.
- Hooks only at the top level of a component, never in conditions or loops.
- Fetch in `useEffect` with an `AbortController` and cleanup, or use the framework's data loader.
- Controlled inputs: `value={text} onChange={(e) => setText(e.target.value)}`.

## Common JS pitfalls

- `this` inside a regular function callback is not the object; use arrow functions or methods.
- `0.1 + 0.2 !== 0.3`; store money as integer cents.
- `new Date(2024, 0, 31)` is January 31: months are 0-based. Store and send dates as ISO strings in UTC (`date.toISOString()`).
- `typeof null === 'object'`; check `value !== null` explicitly.
- `JSON.parse` throws on invalid input; wrap it in `try/catch`.
- `arr.length = 0` and `splice` mutate; `slice` does not.
- Reading `req.body` without `express.json()` gives `undefined`.
- Exporting nothing from a module that another file imports from causes `does not provide an export named`.
