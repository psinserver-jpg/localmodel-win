---
name: coding
description: Write correct, complete, runnable code in any language and modify existing projects safely. Use for any programming, scripting, API, refactoring or code-change task.
triggers: [code, coding, program, programming, script, function, class, module, api, endpoint, backend, cli, python, javascript, typescript, node, java, golang, rust, csharp, cpp, sql, database, refactor, implement, library, package, automation, bug, 코드, 코딩, 프로그램, 프로그래밍, 스크립트, 함수, 클래스, 개발, 구현, 리팩토링, 자동화, 파이썬, 자바스크립트, 타입스크립트, 데이터베이스, 서버, 백엔드]
priority: 40
---
# Coding Skill

Goal: code that runs on the first try, is complete, and fits the project it lives in. When in doubt, choose the simpler, more standard option.

## 1. Understand before writing

- Restate the task in 1-3 lines: inputs (type, format, source), outputs (type, format, destination), and what "done" means.
- List edge cases before coding: empty input, `None`/`null`, zero, negative numbers, very large input, duplicates, non-ASCII text (Korean), missing file, bad network, invalid user input.
- Note constraints: language and version, OS (assume Windows is possible), allowed dependencies, performance needs, required interface.
- If something is ambiguous, pick the most reasonable assumption, state it in one line, and continue. Ask only when you truly cannot proceed.
- For an existing project, READ FIRST: the entry point, the files you will touch, their callers, and the config (`package.json`, `pyproject.toml`, `requirements.txt`, `tsconfig.json`).
- Copy the project's conventions: naming, indentation, quote style, module system (ESM or CommonJS), framework, error-handling style, test layout. Reuse existing helpers instead of writing new ones.
- Do not add a new library when the project or the standard library already does the job.
- Before writing code, list the files you will create or change and what each one is for.

## 2. Completeness rules (most important)

Small models most often fail by leaving work unfinished. These rules are absolute:

- NEVER write placeholders: no `...`, `# rest of code`, `// existing code here`, `// TODO: implement`, `pass` used as a stub, `raise NotImplementedError`, "add your logic here", or "similar to above".
- Output WHOLE files. When you change a file, output the full new content unless the task explicitly asks for a diff.
- Never truncate. If the answer is long, keep going until the last line of the last file. Close every bracket, string, and code fence.
- Every function, class, variable, and file you reference must exist: either you wrote it, it is in the project, or it is in the standard library or a listed dependency.
- Every import is used and correct. Every name you use is imported or defined. No unused variables.
- Implement every requirement from the task. Before finishing, re-read the task and tick each requirement against your code.
- Never silently drop a feature. If a requirement is impossible, say so and why.
- Sample data, config values, and default paths must be real, working values, not `your_value_here`, except for secrets (see section 6).

## 3. Do not invent APIs

- Use only APIs you are certain exist with the exact name, arguments, and return type you are using. If unsure, choose a simpler API you know well.
- Prefer the standard library: Python `pathlib`, `json`, `csv`, `sqlite3`, `argparse`, `logging`, `urllib`; Node `fs/promises`, `path`, `fetch`, `node:test`.
- Otherwise use only well-known, stable libraries (requests, FastAPI, Flask, pytest, Express, React, zod).
- Never invent method names, config keys, CLI flags, or package names. A plausible-looking name that does not exist is a bug.
- Know the major version you target and use its API (pydantic v2 `model_dump()` not v1 `dict()`; React 18+ `createRoot`; Express `express.json()` not `body-parser`).
- List every third-party dependency in `requirements.txt` or `package.json` with a version range (`requests>=2.31,<3`, `"express": "^4.19.2"`).

## 4. Structure

- Small functions (aim under 40 lines) with one responsibility each. Name them with verbs: `load_config`, `parse_row`, `send_email`.
- Clear, specific names: `user_count` not `n`, `invoice_total` not `tmp`. Booleans read as questions: `is_valid`, `has_items`.
- Constants and configuration at the top of the file in UPPER_CASE, or loaded from env vars / a config file.
- No global mutable state. Pass data as arguments and return results.
- Separate layers: input parsing, core logic (pure functions where possible), output and I/O. Core logic should be testable without files or network.
- One module per concern; no circular imports. Python scripts end with `if __name__ == "__main__": main()`.
- Comment only the non-obvious WHY. Docstrings on public functions. No abstraction layers the task does not need.

## 5. Errors and input validation

- Validate at boundaries: user input, CLI args, HTTP requests, file contents, env vars, external API responses. Inside the core, trust validated data.
- Fail with clear, specific messages that say what was wrong and how to fix it: `Config file not found: C:\app\config.json. Create it from config.example.json.`
- Catch specific exceptions only. Never bare `except:` or `except Exception: pass`. Never swallow errors silently; log or re-raise.
- In JS, every `await` that can fail is inside `try/catch` or its promise has `.catch()`. Check `response.ok` after `fetch`.
- Always set timeouts on network calls (`requests.get(url, timeout=10)`).
- Clean up resources: Python `with open(...)`, `with sqlite3.connect(...)` plus `close()`, `try/finally`; JS `try/finally` and `finally` on streams/handles.
- CLI programs exit with non-zero status on failure (`sys.exit(1)`, `process.exitCode = 1`).

## 6. Security basics

- No hard-coded secrets, passwords, API keys, or tokens. Read them from environment variables; provide `.env.example` with dummy names and add `.env` to `.gitignore`.
- SQL: always parameterized queries (`cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`). Never build SQL with f-strings or `+`.
- HTML output: escape user data. In JS use `textContent`, not `innerHTML`, for untrusted text. Use template auto-escaping (Jinja2, React).
- Paths from users: resolve and check they stay inside an allowed base directory.
- Never call `eval`, `exec`, `pickle.loads`, `yaml.load`, or `subprocess` with `shell=True` on user-controlled data. Pass subprocess arguments as a list.
- Hash passwords with bcrypt or argon2, never plain SHA/MD5. Use `secrets` (Python) or `crypto.randomUUID()` / `crypto.randomBytes` (Node) for tokens.
- Do not log secrets or full personal data. Bind dev servers to `127.0.0.1` unless asked otherwise. Never ship `debug=True` as the production default.

## 7. Cross-platform and Windows

- Use `pathlib.Path` (Python) or `path.join` (Node). Never hard-code `/` or `\` separators or absolute user paths like `C:\Users\me`.
- Always pass `encoding="utf-8"` when opening text files in Python. On Windows the default may be cp949 and Korean text breaks. In Node pass `'utf8'`.
- Write CSV with `newline=""` in Python. Use `encoding="utf-8-sig"` if the CSV will be opened in Excel.
- Give run instructions for PowerShell first when the user is on Windows, plus macOS/Linux equivalents. Do not give bash-only commands (`export`, `rm -rf`, `source`, `&&` in Windows PowerShell 5.1) without a PowerShell version.
- Python on Windows: `py -m venv .venv`, `.venv\Scripts\Activate.ps1`, `py -m pip install -r requirements.txt`.
- In `package.json` scripts avoid Unix-only commands; use Node or cross-platform tools (`rimraf`, `cross-env`).

## 8. Mental execution before finishing

Run the code in your head with one concrete sample input and one edge case:

- Walk line by line. Write down variable values at each step.
- Check loop bounds and slicing for off-by-one errors (`range(len(x))`, `< n` vs `<= n`, last element included?).
- Check what happens with empty list, empty string, `None`, zero, missing key, and file not found.
- Check types: string vs number from input (`input()`, query params, and JSON form fields are strings), int vs float division, `Date`/`datetime` timezone.
- Check that every function is called with the right number and order of arguments, and that return values are used.
- Check async code: every async call is awaited, and nothing blocks the event loop.

## 9. Tests and self-checks

- For any non-trivial logic, write runnable tests: `pytest` for Python, `vitest` or `node:test` for JS/TS. Name them `test_<module>.py` / `<module>.test.js`.
- Test the normal case, at least two edge cases, and one error case. Use arrange-act-assert.
- Tests must not need network, real credentials, or a specific machine. Use temporary directories and fakes for external services.
- For small scripts, add a self-check demo: `if __name__ == "__main__":` that runs on sample data, or a few `assert` lines.
- State the exact command to run the tests: `py -m pytest -q` or `npm test`.

## 10. Delivering

Use the output format the task requests. Otherwise:

1. One-paragraph summary of what you built and any assumptions.
2. File tree of all files created or changed.
3. Each file: a line with its relative path, then ONE fenced code block with the language tag and the complete content.
4. Exact setup and run commands, in order: create venv / `npm install`, set env vars, run, test. Include Windows PowerShell commands.
5. Expected output or how to verify it works (example request and response, sample output lines).

## 11. Modifying existing code

- Make the smallest change that fully solves the task. Search for all usages before changing a name or signature.
- Do not rename, reorder, reformat, or "clean up" unrelated code. Keep comments and formatting of untouched lines.
- Keep public interfaces stable: function names, parameters, return types, CLI flags, routes, file formats. If you must change one, update EVERY call site and say so.
- Keep the existing style, libraries, and patterns, even if you would choose differently.
- Update related tests, docs, types, and config when behavior changes. Add a test for the new behavior.
- After the change, re-check imports at the top of each changed file: add what is newly needed, remove what is now unused.
- Explain each change in one line: file, what, why.

## 12. Small-model pitfalls

Check for these mistakes explicitly:

- Mixing languages or versions in one answer: Python 2 syntax (`print "x"`, `except E, e`, `raw_input`), old JS (`var`, callbacks mixed with promises), Python code inside a JS file.
- Mutable default arguments: `def f(items=[])`. Use `items: list | None = None`.
- Forgetting `await`, calling `asyncio.run()` inside a running loop, using `async` callbacks in `forEach` (use `for...of` or `Promise.all`).
- Blocking calls (`time.sleep`, `requests`) inside `async def` handlers.
- JS `==` instead of `===`; `parseInt` without radix; numeric sort without comparator (`arr.sort((a, b) => a - b)`).
- Missing `export` or wrong default vs named import; mixing `require` and `import`; missing `.js` extension on relative ESM imports in Node.
- React: missing `key` on list items, mutating state directly, missing `useEffect` dependencies, calling hooks conditionally.
- Comparing to `None` with `==` instead of `is`; modifying a list while iterating over it.
- Shadowing built-ins or modules (`list = ...`, a file named `json.py` or `requests.py`).
- Integer vs string keys after JSON round-trip; floating point for money (use integer cents or `Decimal`).
- Naive datetimes; JS `Date` months start at 0.
- Relative paths that depend on the current working directory. Build paths from the script location (`Path(__file__).resolve().parent`).
- Wrong indentation that changes Python logic; unclosed brackets at the end of long files.

## Final pass

Before you answer, confirm: every requirement implemented, no placeholders, all files complete, imports correct, dependencies listed, inputs validated, no secrets, UTF-8 everywhere, code traced with a sample input, tests or self-check included, and run commands given.
