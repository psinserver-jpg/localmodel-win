# Coding Review Checklist

## Requirements
- [ ] Every requirement stated in the task is implemented (each one can be pointed to in the code)
- [ ] Assumptions made about ambiguous requirements are stated explicitly in the answer
- [ ] The output format (file type, fields, printed text, HTTP response shape) matches what the task asked for
- [ ] Nothing outside the task scope was added (no unrequested features, frameworks, or rewrites)

## Completeness
- [ ] No placeholder text like `...`, `TODO`, `FIXME`, `rest of code`, `existing code here`, `add your logic here`, `similar to above`
- [ ] No stub bodies (`pass`, `raise NotImplementedError`, empty functions, `return null` stubs) where real logic is required
- [ ] Every file is shown in full from first line to last line, with no truncation and all brackets, strings, and code fences closed
- [ ] Every function, class, method, and file that is referenced is defined in the answer, in the existing project, or in a listed library
- [ ] Every imported name is used and every used name is imported or defined
- [ ] No hard-coded dummy values like `your_value_here` except clearly marked secret names in `.env.example`

## Correctness
- [ ] Only real, existing APIs are used with correct names, argument order, and return types for the stated library version
- [ ] Functions are called with the correct number, order, and types of arguments
- [ ] Loop bounds, indexes, and slices are correct (no off-by-one; first and last elements handled)
- [ ] Empty input, `None`/`null`, zero, and missing keys or files are handled without crashing
- [ ] Values read from input, query strings, env vars, or forms are converted from string to the needed type before use
- [ ] Every async call is awaited (or its promise is returned or handled) and no blocking call runs inside an async handler
- [ ] Python code uses Python 3 syntax only and contains no mutable default arguments
- [ ] JS/TS code uses `===`/`!==`, `const`/`let` (no `var`), and one module system (ESM or CommonJS) consistently

## Structure and Style
- [ ] Functions are small and single-purpose with descriptive names
- [ ] Configuration values and constants are at the top of the file or loaded from env vars or a config file
- [ ] No global mutable state is used to pass data between functions
- [ ] Core logic is separated from I/O (file, network, CLI, UI) so it can be tested on its own
- [ ] The code follows the existing project's naming, formatting, module system, and libraries when modifying a project

## Errors and Resources
- [ ] Input is validated at boundaries (CLI args, HTTP requests, files, env vars, external API responses)
- [ ] Error messages state what went wrong and how to fix it
- [ ] No bare `except:`, no `except Exception: pass`, and no empty `catch {}` blocks
- [ ] Files, connections, and other resources are closed via `with`, `try/finally`, or equivalent
- [ ] Network calls have a timeout and check the response status (`raise_for_status()`, `response.ok`)
- [ ] CLI programs exit with a non-zero status code on failure

## Security
- [ ] No secrets, passwords, API keys, or tokens are hard-coded; they are read from environment variables
- [ ] All SQL uses parameterized queries; no SQL is built with f-strings, `%`, `+`, or template literals
- [ ] Untrusted data inserted into HTML is escaped (no `innerHTML` or `|safe` with user data)
- [ ] No `eval`, `exec`, `pickle.loads`, `yaml.load`, or `shell=True` is used on user-controlled data
- [ ] User-supplied file paths are resolved and checked to stay inside an allowed base directory
- [ ] Passwords are hashed with bcrypt or argon2, not stored in plain text or hashed with MD5/SHA

## Portability
- [ ] Text files are opened with explicit `encoding="utf-8"` (Python) or `'utf8'` (Node)
- [ ] Paths are built with `pathlib`/`path.join` and do not hard-code separators or user-specific absolute paths
- [ ] Paths to bundled files are built relative to the script location, not the current working directory
- [ ] Run instructions include Windows PowerShell commands, and no bash-only command is given without a PowerShell equivalent

## Dependencies, Tests, Delivery
- [ ] Every third-party package used is listed in `requirements.txt`/`pyproject.toml`/`package.json` with a version range, and no unused package is listed
- [ ] Runnable tests or a self-check demo are included covering a normal case, an edge case, and an error case
- [ ] The exact commands to install, run, and test are given in order
- [ ] A file tree lists every created or changed file
- [ ] When modifying existing code, unrelated code is not renamed, reformatted, or removed, and every call site of a changed signature is updated
