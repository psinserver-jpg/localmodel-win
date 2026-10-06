---
name: python
description: Modern Python 3.10+ idioms, project layout, virtual environments on every OS, typing, stdlib tools and minimal correct FastAPI and Flask apps.
triggers: [python, pip, venv, virtualenv, pyproject, requirements.txt, django, flask, fastapi, uvicorn, pandas, numpy, requests, argparse, dataclass, asyncio, pytest, 파이썬, 플라스크, 크롤링, 크롤러, 자동화]
---
# Python Reference (3.10+)

Target Python 3.10 or newer unless the project says otherwise. Never use Python 2 syntax.

## Project layout

Small script or tool:

```
my_tool/
  main.py
  requirements.txt
  README.md
  tests/
    test_main.py
```

Larger app or package:

```
my_app/
  pyproject.toml
  requirements.txt
  src/
    my_app/
      __init__.py
      __main__.py      # enables: python -m my_app
      cli.py
      core.py
  tests/
    test_core.py
```

- Never name your own files after stdlib or installed modules (`json.py`, `random.py`, `requests.py`, `fastapi.py`). They shadow the real module.
- Every package folder you import from needs `__init__.py` (can be empty).
- Run package code with `python -m my_app`, not `python src/my_app/cli.py`, so imports resolve.

## Virtual environments

Always use a venv. Never install into the system Python.

Windows PowerShell:

```
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If activation is blocked by execution policy, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Or skip activation and call the venv interpreter directly: `.venv\Scripts\python.exe main.py`.

Windows cmd: `.venv\Scripts\activate.bat`.

macOS / Linux:

```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

- Always install with `python -m pip`, never bare `pip`, so packages go into the interpreter you run.
- Add `.venv/` to `.gitignore`.

## requirements.txt

List only direct dependencies, with compatible ranges:

```
requests>=2.31,<3
fastapi>=0.110,<1
uvicorn[standard]>=0.29
pydantic>=2.5,<3
```

- Pin exact versions (`==`) only for deployed apps; create them with `python -m pip freeze > requirements.txt` after testing.
- Standard library modules (`json`, `sqlite3`, `pathlib`, `csv`, `argparse`) are never listed.
- Install names differ from import names: `pillow` -> `PIL`, `opencv-python` -> `cv2`, `beautifulsoup4` -> `bs4`, `python-dotenv` -> `dotenv`, `pyyaml` -> `yaml`, `scikit-learn` -> `sklearn`.

## Modern idioms

- f-strings: `f"{name}: {score:.2f}"`, debug form `f"{value=}"`.
- Type hints with built-in generics and `|`: `list[str]`, `dict[str, int]`, `str | None`. No need for `typing.List` or `Optional` in 3.10+.
- `enumerate` and `zip` instead of index loops: `for i, item in enumerate(items, start=1):`. Use `zip(a, b, strict=True)` when lengths must match.
- Comprehensions for simple transforms: `[x.strip() for x in lines if x.strip()]`. Use a normal loop when it gets complex.
- `with` for every file, lock, and connection.
- `is None` / `is not None`, never `== None`.
- Unpacking: `first, *rest = items`, `a, b = b, a`.
- `dict.get(key, default)`, `collections.Counter`, `collections.defaultdict(list)`.
- `sorted(items, key=lambda u: u.age)`; `max(items, key=len)`.
- `pathlib.Path` instead of `os.path`.
- Truthiness: `if items:` for non-empty, but use `if value is not None:` when `0` or `""` are valid.

## Typing and dataclasses

```python
from dataclasses import dataclass, field
from enum import Enum


class Status(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass
class User:
    name: str
    email: str
    status: Status = Status.ACTIVE
    tags: list[str] = field(default_factory=list)  # never tags: list[str] = []

    def is_active(self) -> bool:
        return self.status is Status.ACTIVE


def find_user(users: list[User], email: str) -> User | None:
    for user in users:
        if user.email.lower() == email.lower():
            return user
    return None
```

- Use `@dataclass(frozen=True)` for values that must not change.
- Mutable defaults always via `field(default_factory=...)` in dataclasses, or `None` in functions:

```python
def add_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

## Files and paths

```python
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "items.json"


def load_items(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_items(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
```

- `ensure_ascii=False` keeps Korean readable in JSON files.
- Short forms: `path.read_text(encoding="utf-8")`, `path.write_text(text, encoding="utf-8")`.
- Iterate: `for p in folder.glob("*.txt")`, recursive `folder.rglob("*.py")`.
- `path.stem`, `path.suffix`, `path.name`, `path.with_suffix(".bak")`.

CSV (always `newline=""`; `utf-8-sig` so Excel shows Korean correctly):

```python
import csv
from pathlib import Path


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
```

## Command-line tools with argparse and logging

```python
"""Count words in a text file."""
import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)


def count_words(text: str) -> Counter[str]:
    words = [w.strip(".,!?;:\"'()").lower() for w in text.split()]
    return Counter(w for w in words if w)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Count words in a text file.")
    parser.add_argument("path", type=Path, help="text file to read")
    parser.add_argument("-n", "--top", type=int, default=10, help="how many words to show")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logs")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not args.path.is_file():
        logger.error("File not found: %s", args.path)
        return 1
    if args.top < 1:
        logger.error("--top must be at least 1, got %d", args.top)
        return 1
    text = args.path.read_text(encoding="utf-8")
    logger.debug("Read %d characters", len(text))
    for word, count in count_words(text).most_common(args.top):
        print(f"{count:6d}  {word}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- `main()` returns an exit code; `sys.exit(main())` passes it to the OS.
- Accepting `argv` makes `main` testable: `main(["file.txt", "--top", "3"])`.
- Use `logging` for diagnostics, `print` for the program's actual output. Pass values as arguments (`logger.info("x=%s", x)`), not f-strings.

## Running other programs safely

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    check=False,
    timeout=30,
)
if result.returncode != 0:
    raise RuntimeError(f"git failed: {result.stderr.strip()}")
print(result.stdout)
```

- Pass a LIST of arguments. Never `shell=True` with user input.
- `check=True` raises `subprocess.CalledProcessError` on non-zero exit.
- Windows built-ins like `dir`, `copy`, `del` are not programs; use Python instead (`Path.iterdir`, `shutil.copy`, `Path.unlink`).
- Find an executable: `shutil.which("ffmpeg")` returns `None` if missing; check it and show a clear error.

## HTTP requests

With `requests` (add `requests>=2.31,<3` to requirements):

```python
import requests


def get_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()
```

- Always set `timeout`. Catch `requests.RequestException` at the boundary.
- POST JSON: `requests.post(url, json=payload, timeout=10)`.
- Reuse a `requests.Session()` for many calls to the same host.

Standard library only (no install):

```python
import json
import urllib.request


def get_json_stdlib(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "my-tool/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))
```

`urlopen` raises `urllib.error.HTTPError` for 4xx/5xx and `urllib.error.URLError` for network errors.

## asyncio

```python
import asyncio


async def fetch_one(i: int) -> int:
    await asyncio.sleep(0.1)  # stands in for real async I/O
    return i * 2


async def main() -> None:
    results = await asyncio.gather(*(fetch_one(i) for i in range(5)))
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
```

- `asyncio.run()` exactly once, at the entry point. Inside async code use `await`.
- Never `time.sleep()` or `requests` inside `async def`; use `await asyncio.sleep()` and an async client (`httpx.AsyncClient`), or `await asyncio.to_thread(blocking_func, arg)`.
- Calling an async function without `await` returns a coroutine and does nothing.

## FastAPI minimal app

`requirements.txt`: `fastapi>=0.110,<1` and `uvicorn[standard]>=0.29`. FastAPI uses pydantic v2.

```python
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Items API")


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)


class Item(ItemIn):
    id: int


# In-memory storage for the demo; use a database for real data.
ITEMS: dict[int, Item] = {}


@app.get("/items")
def list_items() -> list[Item]:
    return list(ITEMS.values())


@app.get("/items/{item_id}")
def get_item(item_id: int) -> Item:
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", status_code=201)
def create_item(data: ItemIn) -> Item:
    new_id = max(ITEMS, default=0) + 1
    item = Item(id=new_id, **data.model_dump())
    ITEMS[new_id] = item
    return item
```

Run: `python -m uvicorn main:app --reload`, then open `http://127.0.0.1:8000/docs`.

- Invalid bodies get an automatic 422 response.
- pydantic v2: `model_dump()`, `model_validate()`. Not v1 `dict()` / `parse_obj()`.
- Use `def` endpoints for blocking code, `async def` only when everything inside is awaited.

## Flask minimal app

`requirements.txt`: `flask>=3.0,<4`.

```python
# app.py
from flask import Flask, jsonify, request

app = Flask(__name__)
TODOS: list[dict] = []  # demo storage


@app.get("/todos")
def list_todos():
    return jsonify(TODOS)


@app.post("/todos")
def create_todo():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    todo = {"id": len(TODOS) + 1, "title": title, "done": False}
    TODOS.append(todo)
    return jsonify(todo), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)  # debug only for local development
```

- Templates go in `templates/`, static files in `static/`. Jinja2 auto-escapes HTML; never mark user input `|safe`.
- `request.args.get("page", default=1, type=int)` for query params.

## Common Python pitfalls

- `input()` returns `str`; convert with `int()` inside `try/except ValueError`.
- `/` always gives float; `//` is floor division.
- `list.sort()` returns `None`; use `sorted()` for a new list.
- Do not modify a list while looping over it; build a new list.
- `"a" in my_dict` checks keys, not values.
- Floats for money are inexact; use `decimal.Decimal` or integer cents.
- `datetime.now()` is naive; use `datetime.now(timezone.utc)` for stored timestamps.
- Catch the narrowest exception: `except (ValueError, KeyError) as e:`.
- Late binding in lambdas inside loops: `lambda i=i: i`.
