---
name: testing
description: How to write and run useful automated tests with pytest, unittest, vitest, jest and node test, including fixtures, mocking at boundaries and running tests on Windows.
triggers: [test, tests, testing, unit test, pytest, unittest, vitest, jest, mock, fixture, coverage, tdd, assert, regression, 테스트, 단위테스트, 테스트코드, 검증, 커버리지]
---
# Testing Reference

Tests prove the code works and keep it working. Write tests that run with ONE command, need no network or secrets, and pass on Windows, macOS, and Linux.

## What to test

For each public function or endpoint, cover:

1. **Normal case**: typical input gives the expected output.
2. **Edge cases**: empty input, one element, boundary values (0, -1, max), duplicates, non-ASCII text such as Korean, whitespace.
3. **Error cases**: invalid input raises the right exception or returns the right error status.
4. **Regression**: every bug you fix gets a test that failed before the fix.

Do not test: private helpers directly, third-party library internals, or exact log text. Test behavior through the public interface.

## Structure: arrange, act, assert

```python
def test_apply_discount_reduces_price():
    # Arrange
    cart = Cart(items=[Item("book", 10_000)])
    # Act
    total = cart.total(discount_percent=10)
    # Assert
    assert total == 9_000
```

- One behavior per test. The test name says what is checked: `test_parse_date_rejects_empty_string`.
- Tests are independent: no shared mutable state, no required order.
- Deterministic: no real time, randomness, or network. Inject a clock, a seed, or a fake.
- Keep tests short and obvious; a test with complex logic needs its own test.

## pytest (Python, recommended)

Install: add `pytest>=8` to `requirements-dev.txt` (or `requirements.txt`) and run `python -m pip install pytest`.

Layout:

```
project/
  calc.py
  tests/
    __init__.py        # empty; lets tests import project modules reliably
    test_calc.py
```

Code under test:

```python
# calc.py
def parse_amount(text: str) -> int:
    """Parse '1,234' or ' 500 ' into an int. Raises ValueError on bad input."""
    cleaned = text.replace(",", "").strip()
    if not cleaned:
        raise ValueError("amount is empty")
    if not cleaned.lstrip("-").isdigit():
        raise ValueError(f"not a number: {text!r}")
    return int(cleaned)


def average(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty list")
    return sum(values) / len(values)
```

Tests:

```python
# tests/test_calc.py
import pytest

from calc import average, parse_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("500", 500),
        ("1,234", 1234),
        ("  42 ", 42),
        ("-7", -7),
        ("0", 0),
    ],
)
def test_parse_amount_valid(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "abc", "1.5", "--3"])
def test_parse_amount_invalid_raises(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_average_normal():
    assert average([1.0, 2.0, 3.0]) == pytest.approx(2.0)


def test_average_empty_raises_with_message():
    with pytest.raises(ValueError, match="empty"):
        average([])
```

Run (from the project root, venv active):

```
python -m pytest -q
python -m pytest tests/test_calc.py::test_average_normal -v
python -m pytest -x            # stop at first failure
python -m pytest -k "amount"   # only tests whose name matches
```

On Windows without an active venv: `.venv\Scripts\python.exe -m pytest -q`. Use `python -m pytest`, not bare `pytest`, so the project root is on the import path.

### Fixtures and temporary files

```python
# tests/test_storage.py
import json

import pytest

from storage import load_items, save_items  # functions that take a Path


@pytest.fixture
def data_file(tmp_path):
    """A JSON file inside a fresh temporary directory."""
    path = tmp_path / "items.json"
    path.write_text(json.dumps([{"name": "사과"}]), encoding="utf-8")
    return path


def test_load_items_reads_korean(data_file):
    assert load_items(data_file) == [{"name": "사과"}]


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "sub" / "out.json"
    save_items(path, [{"name": "배"}])
    assert load_items(path) == [{"name": "배"}]


def test_load_missing_file_returns_empty(tmp_path):
    assert load_items(tmp_path / "missing.json") == []
```

- `tmp_path` is a built-in fixture: a unique temporary `pathlib.Path` per test, cleaned up automatically.
- Other built-ins: `monkeypatch` (set env vars, replace attributes), `capsys` (capture printed output).
- Shared fixtures go in `tests/conftest.py`; pytest finds them without imports.

### monkeypatch and capsys

```python
def test_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    assert get_api_key() == "test-key"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        get_api_key()


def test_main_prints_result(capsys):
    exit_code = main(["--name", "Kim"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Hello, Kim" in captured.out
```

### Mocking: only at boundaries

Mock things you do not own and that are slow or non-deterministic: HTTP calls, the clock, email sending, payment APIs. Do NOT mock your own pure logic.

Best option: design for injection, then pass a fake. No mocking library needed:

```python
# weather.py
from collections.abc import Callable

import requests


def fetch_json(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def current_temp(city: str, fetch: Callable[[str], dict] = fetch_json) -> float:
    data = fetch(f"https://api.example.com/weather?city={city}")
    return float(data["temp"])


# tests/test_weather.py
from weather import current_temp


def test_current_temp_uses_fetched_value():
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return {"temp": "21.5"}

    assert current_temp("Seoul", fetch=fake_fetch) == 21.5
    assert "city=Seoul" in calls[0]
```

When injection is not possible, patch the name WHERE IT IS USED, not where it is defined:

```python
from unittest.mock import patch

from weather import current_temp


def test_current_temp_with_patch():
    with patch("weather.fetch_json", return_value={"temp": 30}) as mock_fetch:
        # patching works because the default argument is looked up... only at definition time!
        pass
```

Careful: the example above shows a trap. A default argument (`fetch=fetch_json`) is bound when the function is defined, so patching `weather.fetch_json` later has no effect on it. Patch module-level names that are looked up at call time, for example `patch("weather.requests.get")`:

```python
from unittest.mock import MagicMock, patch

from weather import fetch_json


def test_fetch_json_calls_requests_with_timeout():
    fake_response = MagicMock()
    fake_response.json.return_value = {"temp": 30}
    with patch("weather.requests.get", return_value=fake_response) as mock_get:
        assert fetch_json("https://x.test") == {"temp": 30}
    mock_get.assert_called_once_with("https://x.test", timeout=10)
```

### Testing web apps

FastAPI (needs `httpx` installed):

```python
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_item_returns_201():
    response = client.post("/items", json={"name": "pen", "price": 1.5})
    assert response.status_code == 201
    assert response.json()["name"] == "pen"


def test_create_item_rejects_negative_price():
    response = client.post("/items", json={"name": "pen", "price": -1})
    assert response.status_code == 422
```

Flask:

```python
from app import app


def test_create_todo_requires_title():
    client = app.test_client()
    response = client.post("/todos", json={})
    assert response.status_code == 400
```

## unittest (standard library, no install)

Use when the project already uses it or no dependencies are allowed.

```python
# tests/test_calc_unittest.py
import unittest

from calc import average, parse_amount


class ParseAmountTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_amount("1,234"), 1234)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_amount("")

    def test_average(self):
        self.assertAlmostEqual(average([1.0, 2.0]), 1.5)


if __name__ == "__main__":
    unittest.main()
```

Run: `python -m unittest discover -s tests -v`. Test files must be named `test*.py`. pytest can also run unittest-style tests.

## vitest (JavaScript / TypeScript, recommended)

Works with ESM and TypeScript with zero config. Install: `npm install --save-dev vitest`, then in `package.json`: `"scripts": { "test": "vitest run" }`.

```js
// src/cart.js
export function cartTotal(items, discountPercent = 0) {
  if (!Array.isArray(items)) throw new TypeError('items must be an array');
  if (discountPercent < 0 || discountPercent > 100) {
    throw new RangeError('discountPercent must be between 0 and 100');
  }
  const subtotal = items.reduce((sum, item) => sum + item.price * item.qty, 0);
  return Math.round(subtotal * (100 - discountPercent) / 100);
}
```

```js
// src/cart.test.js
import { describe, it, expect } from 'vitest';
import { cartTotal } from './cart.js';

describe('cartTotal', () => {
  it('sums price times quantity', () => {
    expect(cartTotal([{ price: 1000, qty: 2 }, { price: 500, qty: 1 }])).toBe(2500);
  });

  it('returns 0 for an empty cart', () => {
    expect(cartTotal([])).toBe(0);
  });

  it('applies a discount', () => {
    expect(cartTotal([{ price: 1000, qty: 1 }], 10)).toBe(900);
  });

  it.each([-1, 101])('rejects discount %i', (discount) => {
    expect(() => cartTotal([], discount)).toThrow(RangeError);
  });

  it('rejects non-array input', () => {
    expect(() => cartTotal(null)).toThrow(TypeError);
  });
});
```

Run: `npm test`. Watch mode: `npx vitest`. One file: `npx vitest run src/cart.test.js`.

- `toBe` for primitives, `toEqual` for objects and arrays, `toThrow` with a function wrapper `() => fn()`.
- Async: `await expect(promise).rejects.toThrow('message')`, `await expect(promise).resolves.toEqual(value)`.
- Mock a function: `const fn = vi.fn().mockReturnValue(42);` (import `vi` from `vitest`). Mock `fetch`: `vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: 1 }))))`, and call `vi.unstubAllGlobals()` in `afterEach`.

## jest

Use only if the project already uses jest. Same `describe` / `it` / `expect` API (`jest.fn()` instead of `vi.fn()`). Jest's native ESM support is still experimental and needs extra setup (`node --experimental-vm-modules`); for new ESM or TypeScript projects choose vitest.

## node:test (built in, Node 20+, no install)

```js
// test/cart.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cartTotal } from '../src/cart.js';

test('cartTotal sums items', () => {
  assert.equal(cartTotal([{ price: 100, qty: 3 }]), 300);
});

test('cartTotal rejects bad discount', () => {
  assert.throws(() => cartTotal([], 200), RangeError);
});
```

Run: `node --test` (finds `*.test.js` files and files in `test/` directories automatically). Script: `"test": "node --test"`.

## Running tests on Windows

- PowerShell: `python -m pytest -q` (venv active) or `.venv\Scripts\python.exe -m pytest -q`; `npm test`.
- Test paths: use `tmp_path` / `os.tmpdir()`, never hard-coded `/tmp` or `C:\temp`.
- Always open files with `encoding="utf-8"` in tests too; Korean test data fails on cp949 otherwise.
- Do not compare text with hard-coded `\n` when files were written in text mode on Windows and read in binary mode; read in text mode or normalize with `.splitlines()`.
- Close files and database connections before the test ends; Windows cannot delete open files, so temporary directory cleanup fails.
- Path assertions: compare `Path` objects, not strings with `/`.

## Before delivering tests

- [ ] The test command is stated and runs from the project root.
- [ ] Every test imports only names that exist.
- [ ] Tests cover normal, edge, and error cases.
- [ ] No test depends on network, real credentials, current date, or test order.
- [ ] Test dependencies are listed (`pytest`, `httpx`, `vitest`).
