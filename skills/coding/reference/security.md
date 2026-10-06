---
name: security
description: Condensed OWASP Top 10 with do/don't code for injection, XSS, auth, secrets, path traversal, SSRF, uploads and dependencies.
triggers: [security, secure, auth, login, password, token, jwt, session, xss, csrf, sql injection, injection, upload, secret, api key, encryption, hash, 보안, 로그인, 비밀번호, 인증, 토큰, 암호화, 해킹]
---
# Security Reference

Default to safe. When a shortcut is insecure, do the secure version and keep it simple.

## 1. Injection (SQL, shell, template)

SQL — always parameterize. Never build SQL with f-strings or `+`.

```python
# DON'T
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
# DO (sqlite3 uses ?, psycopg uses %s)
cur.execute("SELECT * FROM users WHERE email = ?", (email,))
```
```js
// DO (node-postgres)
await pool.query('SELECT * FROM users WHERE email = $1', [email]);
```

- Table/column names cannot be parameters: validate against an allow-list (`if col not in {"name", "created_at"}: raise ValueError`).

Shell — pass argument lists, never `shell=True` with user input.

```python
subprocess.run(["git", "log", "-n", str(n)], check=True)          # DO
subprocess.run(f"git log -n {n}", shell=True)                      # DON'T
```
```js
import { execFile } from 'node:child_process';
execFile('git', ['log', '-n', String(n)], (err, out) => {});      // DO, not exec(`git log -n ${n}`)
```

- Never `eval()` / `exec()` / `new Function()` on user input. Use `json.loads` / `JSON.parse` for data, `ast.literal_eval` for Python literals.

## 2. Cross-site scripting (XSS)

- Insert user text with `textContent`, never `innerHTML`:

```js
el.textContent = userComment;          // DO
el.innerHTML = userComment;            // DON'T
```

- Server templates (Jinja2, React, EJS `<%= %>`) escape by default — never disable it (`|safe`, `dangerouslySetInnerHTML`, `<%-`) for user data.
- If HTML from users must be allowed, sanitize with a maintained library (DOMPurify in browser, `bleach`/`nh3` in Python).
- Set `Content-Security-Policy` in production when possible.

## 3. Authentication & passwords

- Hash passwords with a slow, salted algorithm: argon2 (`argon2-cffi`) or bcrypt (`bcrypt`). Never MD5/SHA-1/SHA-256 alone, never store plaintext, never reversible encryption.

```python
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
ok = bcrypt.checkpw(password.encode(), hashed)
```
```js
import bcrypt from 'bcrypt';
const hash = await bcrypt.hash(password, 12);
const ok = await bcrypt.compare(password, hash);
```

- Same error message for "user not found" and "wrong password".
- Rate-limit login endpoints. Lock or slow down after repeated failures.
- Session cookies: `HttpOnly`, `Secure` (HTTPS), `SameSite=Lax`. Regenerate the session id after login.
- JWT: short expiry (15–60 min), verify signature AND algorithm (`algorithms=["HS256"]`), never put secrets in the payload (it is only base64), don't store in `localStorage` if XSS is possible — prefer HttpOnly cookies.
- Random tokens: `secrets.token_urlsafe(32)` (Python), `crypto.randomBytes(32).toString('hex')` / `crypto.randomUUID()` (Node). Never `random` / `Math.random()` for security.
- Compare secrets in constant time: `hmac.compare_digest(a, b)`, `crypto.timingSafeEqual`.

## 4. Authorization

- Check permission on the server for EVERY request, not just by hiding buttons.
- Check ownership: `SELECT ... WHERE id = ? AND owner_id = ?` — never trust an id from the URL alone (IDOR).
- Deny by default; allow explicitly.

## 5. Secrets & configuration

- Never hard-code API keys, passwords, tokens. Read from environment variables:

```python
import os
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise SystemExit("Set the API_KEY environment variable")
```

- Provide `.env.example` with fake values; add `.env` to `.gitignore`.
- Browser JS cannot keep secrets — anything in frontend code is public. Call third-party APIs that need keys from a backend.
- Don't log secrets, passwords, tokens or full card numbers.

## 6. Files & paths

- Path traversal: resolve and verify the path stays inside the allowed folder.

```python
from pathlib import Path
BASE = Path("uploads").resolve()
def safe_path(name: str) -> Path:
    p = (BASE / name).resolve()
    if BASE not in p.parents:
        raise ValueError("invalid path")
    return p
```

- Uploads: limit size, check extension against an allow-list, generate your own filename (`uuid4().hex + ext`), store outside the web root, never execute uploaded files.
- Don't unpickle untrusted data (`pickle.loads`), don't `yaml.load` without `SafeLoader` (use `yaml.safe_load`).

## 7. SSRF & outbound requests

- If the server fetches a URL supplied by a user, allow-list hosts and block private ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, ::1).
- Always set timeouts on HTTP calls (`requests.get(url, timeout=10)`).

## 8. CSRF & CORS

- Cookie-authenticated forms need CSRF protection (framework built-in: Django CSRF, Flask-WTF, `csurf` alternatives) or `SameSite` cookies + checking `Origin`.
- CORS: never `Access-Control-Allow-Origin: *` together with credentials. List exact origins.

## 9. Errors & logging

- Show users a generic message; log details server-side.
- Never return stack traces in production responses (`debug=False`).
- Validate all input at the boundary: type, length, range, format. Reject, don't "fix".

## 10. Dependencies

- Use well-known packages; pin versions (`requirements.txt` with `==`, `package-lock.json` committed).
- Check: `pip-audit`, `npm audit`. Don't install packages with names you are not sure exist (typosquatting).

## Security checklist
- [ ] All SQL parameterized; no string-built queries
- [ ] No `shell=True` / `exec()` with user input; no `eval`
- [ ] User text inserted with `textContent` or auto-escaping templates
- [ ] Passwords hashed with bcrypt/argon2
- [ ] No secrets in code; `.env` ignored; `.env.example` provided
- [ ] File paths validated to stay inside base directory
- [ ] Server-side authorization + ownership checks
- [ ] Timeouts on outbound requests; debug off in production
