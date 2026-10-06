---
name: backend-data
description: REST API design, status codes, validation, SQLite/SQL with parameters, schema migrations, auth basics and environment configuration.
triggers: [backend, server, api, rest, endpoint, database, db, sql, sqlite, postgres, mysql, orm, sqlalchemy, prisma, crud, express, fastapi, flask, django, migration, 백엔드, 서버, 데이터베이스, 디비, 회원가입, 게시판, 쇼핑몰]
---
# Backend & Data Reference

## 1. REST API design

- Resources are plural nouns: `/api/posts`, `/api/posts/{id}`, `/api/posts/{id}/comments`.
- Methods: `GET` read, `POST` create, `PUT` replace, `PATCH` partial update, `DELETE` remove. `GET` never changes data.
- JSON everywhere: `Content-Type: application/json`. Field names consistent (`snake_case` in Python APIs or `camelCase` in JS APIs — pick one).
- Pagination: `GET /api/posts?page=2&limit=20` → `{ "items": [...], "page": 2, "limit": 20, "total": 134 }`. Cap `limit` (e.g. max 100).
- Error body shape (always the same): `{ "error": { "code": "validation_error", "message": "title is required", "field": "title" } }`.
- Version when public: `/api/v1/...`.

### Status codes
| Code | When |
|---|---|
| 200 OK | successful GET/PUT/PATCH |
| 201 Created | POST created a resource (return it, plus `Location` header) |
| 204 No Content | successful DELETE |
| 400 Bad Request | malformed JSON / invalid input |
| 401 Unauthorized | not logged in / bad token |
| 403 Forbidden | logged in but not allowed |
| 404 Not Found | resource does not exist (or not visible to this user) |
| 409 Conflict | duplicate (email already registered), version conflict |
| 422 Unprocessable | validation failed (FastAPI default) |
| 429 Too Many Requests | rate limited |
| 500 Internal Server Error | unexpected bug — log it, return generic message |

## 2. Validation

- Validate at the boundary, before touching the database: required fields, types, lengths, ranges, formats.
- Python: FastAPI + Pydantic models; Flask: manual checks or Pydantic. Node: `zod`.

```python
from pydantic import BaseModel, Field, EmailStr  # EmailStr needs: pip install "pydantic[email]"
class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)
```
```js
import { z } from 'zod';
const PostIn = z.object({ title: z.string().min(1).max(200), body: z.string().min(1).max(20000) });
const parsed = PostIn.safeParse(req.body);
if (!parsed.success) return res.status(400).json({ error: { code: 'validation_error', message: parsed.error.issues[0].message } });
```

## 3. SQLite with the standard library (zero dependencies)

```python
import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).with_name("app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db() -> None:
    with closing(connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

def create_post(title: str, body: str) -> int:
    with closing(connect()) as conn:
        with conn:                           # commits, or rolls back on error
            cur = conn.execute("INSERT INTO posts (title, body) VALUES (?, ?)", (title, body))
        return cur.lastrowid

def list_posts(limit: int = 20, offset: int = 0) -> list[dict]:
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT id, title, body, created_at FROM posts ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
```

Notes:
- `with conn:` handles commit/rollback but does NOT close; use `closing()`.
- Always `?` placeholders. Add indexes for columns used in `WHERE`/`ORDER BY`: `CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);`.
- Store times as ISO-8601 UTC text or Unix integers; be consistent.
- Unique constraint for emails: `email TEXT NOT NULL UNIQUE` → catch `sqlite3.IntegrityError` → 409.

## 4. Migrations

- Small projects: keep numbered SQL files (`migrations/001_init.sql`, `002_add_tags.sql`) and a `schema_version` table; apply files with a higher number in order inside a transaction.
- With an ORM: SQLAlchemy → Alembic (`alembic revision --autogenerate -m "msg"`, `alembic upgrade head`); Prisma → `npx prisma migrate dev`; Django → `python manage.py makemigrations && python manage.py migrate`.
- Never edit a migration that already ran in production; add a new one.

## 5. Auth basics

- Passwords: bcrypt/argon2 (see security reference). Email unique, lower-cased before saving.
- Sessions (server-rendered apps): framework session with HttpOnly cookie. Simplest and safest.
- Tokens (SPA/mobile): short-lived access token + refresh token; store refresh token in HttpOnly cookie.
- Protect routes with one middleware/dependency, not copy-pasted checks.

## 6. Configuration & environment

```
# .env.example (commit this; never commit .env)
DATABASE_URL=sqlite:///app.db
SECRET_KEY=change-me
PORT=8000
```

- Python: `os.environ.get("PORT", "8000")`; optional `python-dotenv` (`from dotenv import load_dotenv; load_dotenv()`).
- Node 20.6+: `node --env-file=.env server.js`, or the `dotenv` package.
- Bind to `127.0.0.1` for local dev; `0.0.0.0` only when it must be reachable from other machines.

## 7. Minimal server skeletons

FastAPI:
```python
# pip install fastapi uvicorn
from fastapi import FastAPI, HTTPException
app = FastAPI()
POSTS: dict[int, dict] = {}

@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    if post_id not in POSTS:
        raise HTTPException(status_code=404, detail="post not found")
    return POSTS[post_id]
# run: uvicorn main:app --reload
```

Express:
```js
// npm install express
import express from 'express';
const app = express();
app.use(express.json());
const posts = new Map();
app.get('/api/posts/:id', (req, res) => {
  const post = posts.get(Number(req.params.id));
  if (!post) return res.status(404).json({ error: { code: 'not_found', message: 'post not found' } });
  res.json(post);
});
app.use((err, req, res, next) => { console.error(err); res.status(500).json({ error: { code: 'internal', message: 'Internal error' } }); });
app.listen(process.env.PORT || 3000, () => console.log('http://localhost:' + (process.env.PORT || 3000)));
// package.json needs "type": "module" for import syntax
```

## 8. Frontend ↔ backend

- Serving a frontend from a different port causes CORS errors: enable CORS for the exact dev origin (FastAPI `CORSMiddleware`, Express `cors({ origin: 'http://localhost:5173' })`) or serve the frontend from the same server.
- Always handle `!response.ok` in `fetch` and show the error to the user.
