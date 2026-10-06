---
name: git-tooling
description: Git basics and safe workflows, .gitignore templates for Python and Node, conventional commits, linters and formatters (ruff, black, eslint, prettier).
triggers: [git, github, commit, branch, merge, rebase, pull request, gitignore, lint, linter, formatter, ruff, black, eslint, prettier, pre-commit, ci, github actions, 깃, 깃허브, 커밋, 브랜치, 린트]
---
# Git & Tooling Reference

## 1. Everyday git

```bash
git status                          # always check before committing
git add path/to/file                # stage specific files (avoid blind `git add .` in unknown repos)
git commit -m "feat: add contact form validation"
git switch -c feature/contact-form  # new branch (older git: git checkout -b)
git push -u origin feature/contact-form
git pull --rebase origin main       # update your branch with main
git log --oneline -n 10
git diff                            # unstaged changes; `git diff --staged` for staged
```

- Never commit secrets, `.env`, `node_modules/`, virtualenvs, build output, or large binaries.
- Dangerous commands — only when the user explicitly asks: `git reset --hard`, `git push --force`, `git clean -fd`, rewriting shared history. Prefer `git push --force-with-lease` over `--force`.
- Undo safely: `git restore file` (discard working changes to a file), `git restore --staged file` (unstage), `git revert <commit>` (undo a pushed commit with a new commit).
- Merge conflict: open files, resolve between `<<<<<<<` / `=======` / `>>>>>>>`, remove markers, `git add`, then `git commit` (merge) or `git rebase --continue`.

## 2. Commit messages (Conventional Commits)

```
<type>(optional scope): <short imperative summary, ≤ 72 chars>

<optional body: why, not how>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Examples:
- `feat(auth): add password reset email`
- `fix: handle empty cart in checkout total`

One logical change per commit.

## 3. .gitignore templates

Python:
```
__pycache__/
*.py[cod]
.venv/
venv/
.env
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
*.db
```

Node:
```
node_modules/
dist/
build/
.env
.env.local
npm-debug.log*
.next/
coverage/
.DS_Store
```

Always add OS/editor files if useful: `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/` (unless the team shares settings).

## 4. Python tooling

- Ruff = linter + formatter (fast, replaces flake8/isort/black for most projects):
```bash
pip install ruff
ruff check .          # lint
ruff check . --fix    # auto-fix
ruff format .         # format (black-compatible)
```
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```
- Black alone: `pip install black && black .`
- Type check: `pip install mypy && mypy src/`

## 5. JavaScript/TypeScript tooling

```bash
npm install -D eslint prettier
npx eslint --init            # or: npm init @eslint/config@latest
npx eslint .
npx prettier --write .
```
```json
// .prettierrc
{ "semi": true, "singleQuote": true, "printWidth": 100, "trailingComma": "all" }
```
- package.json scripts so everyone runs the same commands:
```json
"scripts": { "dev": "vite", "build": "vite build", "lint": "eslint .", "format": "prettier --write .", "test": "vitest run" }
```
- TypeScript check without building: `npx tsc --noEmit`.

## 6. pre-commit (optional)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```
`pip install pre-commit && pre-commit install`

## 7. Minimal GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: python -m pytest -q
```
Node variant: `actions/setup-node@v4` with `node-version: 20`, then `npm ci` and `npm test`.

## 8. README essentials for any deliverable

1. One-line description.
2. Requirements (Python 3.10+, Node 20+).
3. Install commands (both PowerShell and bash if they differ).
4. Run command and the URL/port to open.
5. Configuration (`.env` variables).
6. How to run tests.
