import tempfile
import unittest
from pathlib import Path

from lmw.client import ChatResult, strip_reasoning
from lmw.config import Config
from lmw.parse import apply_edits, parse_file_blocks, parse_steps, parse_verdict, parse_issues
from lmw.pipeline import Pipeline, _merge_continuation
from lmw.checks import run_checks, has_errors
from lmw.workspace import Workspace, UnsafePathError

ANALYSIS = """## Goal
A page
## Acceptance criteria
1. index.html exists with a title
## Constraints
- none
## Questions
- none
"""
PLAN = """## Approach
One file.
## Files
- index.html — page
## Steps
### Step 1: Page
Files: index.html
Do: write it
## Verification
- 1 -> step 1
"""
GOOD_HTML = """=== FILE: index.html ===
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>T</title></head>
<body><main><h1>안녕</h1><a href="#x">x</a><section id="x">s</section></main></body></html>
=== END FILE ===
STEP DONE: ok"""
BAD_HTML = GOOD_HTML.replace('id="x"', 'id="y"')


class FakeClient:
    def __init__(self, first_html):
        self.html = first_html
        self.calls = []

    def chat(self, messages, temperature=None, max_tokens=None, on_token=None):
        p = messages[1]["content"]
        self.calls.append(p.split("\n", 1)[0])
        if "PHASE 1" in p or "PHASE 2" in p:
            return ChatResult(ANALYSIS, "stop")
        if "PHASE 3" in p:
            return ChatResult(PLAN, "stop")
        if "PHASE 4" in p:
            return ChatResult("## Coverage\n- 1 -> Step 1\n## Issues\n- none\n## VERDICT: PASS", "stop")
        if "PHASE 5" in p:
            return ChatResult(self.html, "stop")
        if "PHASE 6" in p:
            return ChatResult("## Criteria\n1. PASS — ok\n## Issues\n- none\n## VERDICT: PASS", "stop")
        if "PHASE 7" in p:
            return ChatResult(GOOD_HTML, "stop")
        return ChatResult("## Summary\ndone", "stop")


class PipelineTest(unittest.TestCase):
    def _run(self, html):
        d = Path(tempfile.mkdtemp())
        cfg = Config(interactive=False)
        fake = FakeClient(html)
        pipe = Pipeline(cfg, d, request="랜딩 페이지 만들어줘", client=fake)
        state = pipe.run()
        return d, state, fake

    def test_happy_path(self):
        d, state, fake = self._run(GOOD_HTML)
        self.assertEqual(state["status"], "done")
        self.assertTrue((d / "index.html").is_file())
        self.assertGreaterEqual(state["review_round"], 2)  # min review rounds

    def test_check_error_forces_fix(self):
        d, state, fake = self._run(BAD_HTML)
        self.assertTrue(any("PHASE 7" in c for c in fake.calls))
        self.assertIn('id="x"', (d / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "done")


class ParseTest(unittest.TestCase):
    def test_blocks_and_truncation(self):
        out = parse_file_blocks("=== FILE: a.py ===\nprint(1)\n=== END FILE ===\n=== FILE: b.py ===\nx=")
        self.assertEqual([b.path for b in out.blocks], ["a.py", "b.py"])
        self.assertTrue(out.truncated)

    def test_fenced_fallback(self):
        out = parse_file_blocks("### index.html\n```html\n<p>hi</p>\n```\n")
        self.assertEqual(out.blocks[0].path, "index.html")

    def test_edit_fuzzy(self):
        new, failed = apply_edits("def f():\n    return 1\n", parse_file_blocks(
            "=== EDIT: a.py ===\n<<<<<<< SEARCH\nreturn 1\n=======\n    return 2\n>>>>>>> REPLACE\n=== END EDIT ===").blocks[0].edits)
        self.assertEqual(failed, [])
        self.assertIn("return 2", new)

    def test_steps_verdict_issues(self):
        self.assertEqual(parse_steps(PLAN)[0].files, ["index.html"])
        self.assertEqual(parse_verdict("x\n## VERDICT: **FAIL**"), "FAIL")
        self.assertEqual(parse_issues("## Issues\n- [major] a.py: bad → fix")[0].severity, "major")

    def test_reasoning_and_merge(self):
        self.assertEqual(strip_reasoning("<think>hmm</think>answer"), "answer")
        self.assertEqual(_merge_continuation("start: the quick brown fox jumps", "the quick brown fox jumps over"), "start: the quick brown fox jumps over")


class ChecksTest(unittest.TestCase):
    def test_placeholders_and_paths(self):
        ws = Workspace(Path(tempfile.mkdtemp()))
        ws.write("a.js", "function f() {\n  // ... rest of code\n}\n")
        ws.write("todo.py", "todos = ['Todo list']\n")
        self.assertTrue(has_errors(run_checks(ws, ["a.js"])))
        self.assertFalse(has_errors(run_checks(ws, ["todo.py"])))
        with self.assertRaises(UnsafePathError):
            ws.resolve("../evil.txt")


if __name__ == "__main__":
    unittest.main()
