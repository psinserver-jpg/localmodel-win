---
name: debugging
description: Systematically find and fix bugs, errors, crashes and failing tests by reproducing, locating and fixing the root cause. Use when something is broken, throws an error or behaves wrongly.
triggers: [error, traceback, exception, bug, fix, crash, debug, failing, fails, broken, not working, doesnt work, stack trace, undefined, segfault, 에러, 오류, 버그, 안돼, 안됨, 작동안함, 고쳐, 수정, 디버그, 디버깅, 실패, 문제]
priority: 45
---
# Debugging Skill

Goal: find the ROOT CAUSE, fix it with the smallest correct change, and prove the fix works. Never guess-and-patch.

## Workflow

1. **Reproduce.** Get the exact command, input, and environment (OS, language version, package versions) that triggers the bug. Write down expected vs actual behavior. If you cannot run code, give the user exact steps to run.
2. **Read the full error.** Python traceback bottom-up: last line is the error type and message, the frame above it is where it happened; walk up to the first frame in the user's own code, not library code. JS: read the message, then the first stack frame in the user's files. Quote the key line.
3. **Locate.** Open the file and line from the error. Read the whole function and its callers. Check what values the variables can actually hold there.
4. **Form 2-3 hypotheses, ranked by likelihood.** Each one must explain ALL the symptoms. Example: "1. `config` is `None` because the path is relative to the wrong directory. 2. The key is `userName`, not `username`."
5. **Verify the cheapest hypothesis first.** Add a temporary print or log of the exact values (`print(repr(x), type(x))`, `console.log(JSON.stringify(x))`), check versions (`py -m pip show <pkg>`, `npm ls <pkg>`), or build a minimal repro of 5-15 lines. Change one thing at a time.
6. **Fix the root cause, not the symptom.** Do not wrap it in `try/except: pass`, add `if x is not None` without knowing why `x` is `None`, or hard-code a value. Fix where the bad value is created.
7. **Verify.** Re-run the original reproduction and the existing tests. Add a regression test that fails before the fix and passes after. Check that other callers of the changed code still work. Remove temporary debug prints.
8. **Explain** in 2-4 lines: cause, why it produced this error, what you changed, how you verified it.

## Rules

- Output the complete fixed file or function, following the coding skill completeness rules. No `...` placeholders.
- Change as little as possible. Do not refactor or reformat unrelated code while fixing a bug.
- If the error comes from the environment (missing package, wrong Python, PATH, port in use), fix the environment with exact commands instead of changing code.
- If you lack information (no traceback, no code), ask for the exact error text and the command that was run; meanwhile list the most likely causes.
- Check the obvious first: file saved, correct file running, correct venv active, server restarted, browser cache cleared, dependencies installed.

## Python errors

| Error | Usual cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'x'` | Package not installed in the active interpreter, venv not active, or wrong package name (`cv2` is `opencv-python`, `PIL` is `pillow`) | Install with the interpreter that runs the script: `python -m pip install x` (venv active) or `py -m pip install x`; check `python -c "import sys; print(sys.executable)"` |
| `ImportError: cannot import name 'x'` | Name does not exist in that version, circular import, or your file shadows a module (`json.py`, `requests.py`) | Check version and spelling; rename shadowing files; move the import inside a function to break a cycle |
| `IndentationError` / `TabError` | Mixed tabs and spaces or misaligned block | Use 4 spaces only; re-indent the whole block |
| `SyntaxError` | Missing `:`, bracket, or quote, often on the line BEFORE the reported one; Python 2 syntax | Check the previous line for unclosed brackets |
| `KeyError: 'x'` | Dict key missing or spelled differently | Print `d.keys()`; use `d.get("x")` only if missing is a valid case |
| `TypeError: 'NoneType' object is not subscriptable` / `has no attribute` | A function returned `None` (no `return`, failed lookup, in-place method like `list.sort()`) | Trace where the value was assigned; fix the function that returns `None` |
| `TypeError: can only concatenate str (not "int")` | Mixing str and int | Convert: `int(s)`, or use an f-string |
| `UnicodeDecodeError: 'cp949' codec can't decode` (or `UnicodeEncodeError` on print) | Windows default encoding cp949 used for UTF-8 data | `open(path, encoding="utf-8")`; Excel CSV `utf-8-sig`; console: `$env:PYTHONUTF8="1"` |
| `FileNotFoundError` | Relative path resolved against the current directory, not the script | `Path(__file__).resolve().parent / "data.txt"` |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | Calling `asyncio.run` inside Jupyter or async code | Use `await main()` instead |

## JavaScript / Node errors

| Error | Usual cause | Fix |
|---|---|---|
| `TypeError: Cannot read properties of undefined (reading 'x')` | Object is `undefined`: data not loaded yet, wrong JSON path, missing `return`, missing `await` | Log the parent object; await the data; use `obj?.x` only if undefined is valid |
| `TypeError: x is not a function` | Wrong import (default vs named), typo, value is not what you think, missing `export` | `console.log(typeof x, x)`; match `export default` with `import x`, `export function x` with `import { x }` |
| `ERR_MODULE_NOT_FOUND` | Missing `.js` extension in relative ESM import, wrong path, or package not installed | `import { a } from './a.js'`; run `npm install` |
| `Cannot use import statement outside a module` / `require is not defined in ES module scope` | Mixing ESM and CommonJS | Pick one: `"type": "module"` in `package.json` plus `import` everywhere, or `require` everywhere (`.cjs`/`.mjs` per file) |
| `EADDRINUSE: address already in use :::3000` | Another process (often an old server you started) holds the port | Kill it (commands below) or use another `PORT` |
| `npm ERR! ERESOLVE unable to resolve dependency tree` | Peer dependency version conflict | Align versions to compatible ones; `npm install --legacy-peer-deps` only as a last resort and say so |
| `Access to fetch ... blocked by CORS policy` | Server does not send `Access-Control-Allow-Origin` for the page origin | Fix on the SERVER (Express `cors({ origin: 'http://localhost:5173' })`, FastAPI `CORSMiddleware`) or use the dev-server proxy; never fix in client code |
| `Unexpected token '<' ... is not valid JSON` | Server returned HTML (404 page, error page) instead of JSON | Log `res.status` and `await res.text()`; fix the URL or server error |
| `UnhandledPromiseRejection` | Rejected promise with no `catch` | Wrap `await` in `try/catch`; add `.catch()` |

## Windows environment problems

| Symptom | Cause | Fix |
|---|---|---|
| `'pip' is not recognized` / `'python' is not recognized` | Python not on PATH | Use the launcher: `py -m pip install x`, `py script.py`; or reinstall with "Add to PATH" |
| `python` opens Microsoft Store | App execution alias | Use `py`, or disable the alias in Settings > Apps > Advanced app settings > App execution aliases |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or skip activation: `.venv\Scripts\python.exe script.py` |
| `rm -rf`, `export`, `source` fail | Bash commands in PowerShell/cmd | `Remove-Item -Recurse -Force dir`, `$env:NAME="value"`, `.venv\Scripts\Activate.ps1` |
| Korean text shows as garbage | cp949 vs UTF-8 mismatch | Save files as UTF-8; `chcp 65001`; read with `encoding="utf-8"` |

Free a port on Windows (PowerShell or cmd), replacing 3000 and the PID:

```
netstat -ano | findstr :3000
taskkill /PID 12345 /F
```

macOS/Linux: `lsof -i :3000` then `kill 12345`.
