"""Deterministic, tool-based checks. The model can be wrong about its own output;
these checks cannot be talked out of. Errors block the PASS verdict."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote, urlparse

from .workspace import Workspace


@dataclass
class Finding:
    level: str  # "error" or "warning"
    file: str
    message: str

    def __str__(self) -> str:
        return "%s %s: %s" % (self.level.upper(), self.file or "(project)", self.message)


# --------------------------------------------------------------- placeholders

_C = r"(?://|#|/\*|<!--|\*|--|;)\s*"  # a comment opener
PLACEHOLDER_PATTERNS = [
    # (pattern, message, case_sensitive)
    (_C + r"\.\.\.\s*(\*/|-->)?\s*$", "ellipsis placeholder comment", False),
    (r"^\s*\.\.\.\s*$", "bare '...' line (omitted code?)", False),
    (_C + r".*\b(rest|remainder) of (the )?(code|file|implementation|content|styles?|logic)\b", "'rest of code' placeholder", False),
    (r"\b(your|add|insert|put) (your |the )?(code|content|logic|text|implementation) here\b", "'add code here' placeholder", False),
    (_C + r".*\b(same as (before|above)|existing code( here)?|unchanged)\s*(\.{3})?\s*(\*/|-->)?\s*$", "'same as before' placeholder", False),
    (_C + r"(TODO|FIXME|XXX)\b", "TODO/FIXME marker", True),
    (r"\blorem ipsum\b", "lorem ipsum filler text", False),
    (r"(여기에|이곳에).{0,20}(구현|작성|추가|입력)(하세요|합니다|해주세요|필요)", "Korean 'implement here' placeholder", False),
    (r"\((생략|중략|이하 생략)\)|\.\.\.\s*생략", "Korean '(생략)' placeholder", False),
    (_C + r".*\bimplement(ation)? (goes )?here\b", "'implement here' placeholder", False),
]
_PLACEHOLDER_RES = [
    (re.compile(p, re.MULTILINE if cs else re.IGNORECASE | re.MULTILINE), msg)
    for p, msg, cs in PLACEHOLDER_PATTERNS
]

CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css", ".scss",
            ".java", ".go", ".rs", ".c", ".cpp", ".h", ".cs", ".php", ".rb", ".kt", ".swift", ".vue",
            ".svelte", ".sh", ".ps1", ".bat", ".sql", ".json", ".yml", ".yaml", ".toml"}


def check_placeholders(path: str, text: str) -> List[Finding]:
    out = []
    for rx, msg in _PLACEHOLDER_RES:
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            line = text.split("\n")[line_no - 1].strip()
            # Python's `...` is legal in type stubs/Protocols; spread `...x` is legal in JS.
            if msg.startswith("bare") and path.endswith((".pyi",)):
                continue
            out.append(Finding("error", path, "line %d: %s: %s" % (line_no, msg, line[:120])))
            break
    return out


# ----------------------------------------------------------------------- HTML

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}
STRICT = {"html", "head", "body", "div", "section", "main", "header", "footer", "nav", "article",
          "aside", "ul", "ol", "form", "table", "button", "a", "span", "script", "style", "label",
          "select", "textarea", "h1", "h2", "h3", "h4", "h5", "h6", "dialog", "details", "summary",
          "figure", "svg", "template"}


class _HTMLCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: List[tuple] = []
        self.errors: List[str] = []
        self.ids: Dict[str, int] = {}
        self.anchors: List[str] = []
        self.refs: List[tuple] = []  # (attr, url, line)
        self.imgs_without_alt: List[int] = []
        self.has_viewport = False
        self.has_title = False
        self.html_lang = None
        self.scripts: List[tuple] = []  # (code, line, is_module)
        self._script_buf: Optional[List[str]] = None
        self._script_line = 0
        self._script_module = False
        self._in_svg = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if tag == "svg":
            self._in_svg += 1
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag == "meta" and (a.get("name") or "").lower() == "viewport":
            self.has_viewport = True
        if tag == "title":
            self.has_title = True
        if "id" in a and a["id"]:
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt.append(line)
        for attr in ("href", "src"):
            v = a.get(attr)
            if v:
                if v.startswith("#") and len(v) > 1:
                    self.anchors.append(v[1:])
                else:
                    self.refs.append((attr, v, line))
        if tag == "script" and not a.get("src"):
            t = (a.get("type") or "").lower()
            if t in ("", "text/javascript", "module", "application/javascript"):
                self._script_buf = []
                self._script_line = line
                self._script_module = t == "module"
        if tag not in VOID and not (self._in_svg and tag != "svg"):
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        # <br/>, <path/> ... ; record attributes but do not push.
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        if tag == "svg":
            self._in_svg -= 1

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag == "script" and self._script_buf is not None:
            self.scripts.append(("".join(self._script_buf), self._script_line, self._script_module))
            self._script_buf = None
        if self._in_svg and tag != "svg":
            return
        if tag == "svg":
            self._in_svg = max(0, self._in_svg - 1)
        if tag in VOID:
            return
        # pop to the matching tag; report unclosed STRICT tags we skip over
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, l in self.stack[i + 1:]:
                    if t in STRICT:
                        self.errors.append("<%s> opened on line %d is not closed before </%s> on line %d" % (t, l, tag, line))
                del self.stack[i:]
                return
        if tag in STRICT:
            self.errors.append("stray closing </%s> on line %d" % (tag, line))

    def handle_data(self, data):
        if self._script_buf is not None:
            self._script_buf.append(data)


def _is_local_ref(url: str) -> bool:
    if not url or url.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "{{", "${", "blob:")):
        return False
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc and not url.startswith("//")


def check_html(ws: Workspace, path: str, text: str, node: Optional[str]) -> List[Finding]:
    out: List[Finding] = []
    p = _HTMLCollector()
    try:
        p.feed(text)
        p.close()
    except Exception as e:  # html.parser is lenient; this is rare
        out.append(Finding("error", path, "HTML could not be parsed: %s" % e))
        return out
    is_document = bool(re.search(r"<html[\s>]", text, re.IGNORECASE))
    for t, l in p.stack:
        if t in STRICT:
            out.append(Finding("error", path, "<%s> opened on line %d is never closed" % (t, l)))
    for e in p.errors[:10]:
        out.append(Finding("error", path, e))
    if is_document:
        if not re.match(r"\s*<!doctype html", text, re.IGNORECASE):
            out.append(Finding("warning", path, "missing <!DOCTYPE html> at the top"))
        if not p.has_viewport:
            out.append(Finding("error", path, 'missing <meta name="viewport" content="width=device-width, initial-scale=1"> (breaks mobile layout)'))
        if not p.has_title:
            out.append(Finding("warning", path, "missing <title>"))
        if not p.html_lang:
            out.append(Finding("warning", path, "missing lang attribute on <html>"))
    for line in p.imgs_without_alt[:5]:
        out.append(Finding("warning", path, "<img> on line %d has no alt attribute" % line))
    for id_, n in p.ids.items():
        if n > 1:
            out.append(Finding("error", path, "duplicate id=\"%s\" (%d times)" % (id_, n)))
    for anchor in sorted(set(p.anchors)):
        if anchor not in p.ids and anchor != "top":
            out.append(Finding("error", path, 'link to "#%s" but no element has id="%s"' % (anchor, anchor)))
    base = (ws.root / path).parent
    for attr, url, line in p.refs:
        if not _is_local_ref(url):
            continue
        target = unquote(urlparse(url).path)
        if not target:
            continue
        resolved = (base / target).resolve() if not target.startswith("/") else (ws.root / target.lstrip("/")).resolve()
        if resolved.is_dir():
            resolved = resolved / "index.html"
        if not resolved.exists():
            out.append(Finding("error", path, '%s="%s" on line %d points to a file that does not exist' % (attr, url, line)))
    if node:
        for code, line, is_module in p.scripts:
            if code.strip():
                err = _node_check(node, code, ".mjs" if is_module else ".js")
                if err:
                    out.append(Finding("error", path, "inline <script> starting line %d has a syntax error: %s" % (line, err)))
    return out


# ------------------------------------------------------------------ other langs

def _strip_css_comments_strings(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "\"\"", css)


def check_css(path: str, text: str) -> List[Finding]:
    s = _strip_css_comments_strings(text)
    depth = 0
    for i, ch in enumerate(s):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return [Finding("error", path, "unexpected '}' near line %d" % (s.count("\n", 0, i) + 1))]
    if depth > 0:
        return [Finding("error", path, "%d unclosed '{' (file truncated?)" % depth)]
    return []


def check_python(path: str, text: str) -> List[Finding]:
    try:
        compile(text, path, "exec")
    except SyntaxError as e:
        return [Finding("error", path, "SyntaxError line %s: %s" % (e.lineno, e.msg))]
    except ValueError as e:
        return [Finding("error", path, str(e))]
    return []


def check_json(path: str, text: str) -> List[Finding]:
    if path.endswith(("tsconfig.json", "jsconfig.json")) or "/.vscode/" in path:
        return []  # these allow comments
    try:
        json.loads(text)
    except ValueError as e:
        return [Finding("error", path, "invalid JSON: %s" % e)]
    return []


def _node_check(node: str, code: str, suffix: str) -> Optional[str]:
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as fh:
        fh.write(code)
        tmp = fh.name
    try:
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip().splitlines()
            # keep the informative lines, drop the temp path noise
            useful = [l for l in msg if l.strip() and tmp not in l and not l.startswith("    at ")]
            return " | ".join(useful[:4]) or "syntax error"
        return None
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        try:
            Path(tmp).unlink()
        except OSError:
            pass


def check_js(path: str, text: str, node: Optional[str]) -> List[Finding]:
    if not node:
        return []
    ext = Path(path).suffix
    is_module = ext == ".mjs" or bool(re.search(r"^\s*(import\s|export\s)", text, re.MULTILINE))
    err = _node_check(node, text, ".mjs" if is_module else ".cjs" if ext == ".cjs" else ".js")
    return [Finding("error", path, "syntax error: %s" % err)] if err else []


# ------------------------------------------------------------------- commands

def run_command(cmd: str, cwd: Path, timeout: int) -> Finding:
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return Finding("error", "", "command `%s` timed out after %ds" % (cmd, timeout))
    output = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
    tail = output[-2500:]
    if r.returncode != 0:
        return Finding("error", "", "command `%s` failed (exit %d):\n%s" % (cmd, r.returncode, tail))
    return Finding("ok", "", "command `%s` passed" % cmd)


# ---------------------------------------------------------------------- driver

def run_checks(ws: Workspace, files: List[str], commands: Optional[List[str]] = None,
               timeout: int = 300) -> List[Finding]:
    node = shutil.which("node")
    findings: List[Finding] = []
    for f in files:
        text = ws.read(f)
        if text is None:
            continue
        ext = Path(f).suffix.lower()
        if ext in CODE_EXT or ext in (".md", ".txt"):
            if ext not in (".md", ".txt"):
                findings += check_placeholders(f, text)
        if ext in (".html", ".htm"):
            findings += check_html(ws, f, text, node)
        elif ext in (".css",):
            findings += check_css(f, text)
        elif ext == ".py":
            findings += check_python(f, text)
        elif ext == ".json":
            findings += check_json(f, text)
        elif ext in (".js", ".mjs", ".cjs"):
            findings += check_js(f, text, node)
    for cmd in commands or []:
        findings.append(run_command(cmd, ws.root, timeout))
    return findings


def format_findings(findings: List[Finding]) -> str:
    if not findings:
        return "All automated checks passed (syntax, placeholders, references)."
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warning"]
    oks = [f for f in findings if f.level == "ok"]
    lines = []
    if errors:
        lines.append("ERRORS (must fix):")
        lines += ["- " + str(f) for f in errors]
    if warns:
        lines.append("WARNINGS (should fix):")
        lines += ["- " + str(f) for f in warns]
    if oks:
        lines += ["- " + f.message for f in oks]
    if not errors:
        lines.insert(0, "No blocking errors.")
    return "\n".join(lines)


def has_errors(findings: List[Finding]) -> bool:
    return any(f.level == "error" for f in findings)
