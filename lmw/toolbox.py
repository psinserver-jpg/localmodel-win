"""More tools for the agent: files, running things, knowledge, planning and sub-agents.

Each tool is a small function `fn(tools, **args) -> (ok, summary, output, extra)` registered with @tool.
`tools` is the agent's `Tools` object (project folder, workspace helpers, callbacks set by the Agent).
Permissions follow the tool's class: "read" runs freely, "edit" asks in the default mode, "run" asks unless
the user chose full access (see classify()).
"""

from __future__ import annotations

import ast
import math
import operator
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import netutil
from .skills import trigger_score
from .workspace import IGNORE_DIRS

S = {"type": "string"}
I = {"type": "integer"}
B = {"type": "boolean"}
A = {"type": "array", "items": {"type": "string"}}
GROUPS = (("files", "Files"), ("run", "Run"), ("know", "Know/plan"))


@dataclass
class ToolDef:
    name: str
    group: str
    sig: str
    desc: str
    props: Dict[str, dict]
    required: List[str]
    perm: str  # read | edit | run
    label: str
    fn: Callable


EXTRAS: Dict[str, ToolDef] = {}


def tool(name: str, group: str, sig: str, desc: str, props: Dict[str, dict], required: Tuple[str, ...] = (),
         perm: str = "read", label: str = ""):
    def deco(fn: Callable) -> Callable:
        EXTRAS[name] = ToolDef(name, group, sig, desc, props, list(required), perm, label or name, fn)
        return fn
    return deco


def call(t, name: str, args: Dict):
    return EXTRAS[name].fn(t, **args)


def labels() -> Dict[str, str]:
    return {n: d.label for n, d in EXTRAS.items()}


# ------------------------------------------------------------ permissions

READ_GIT = {"status", "diff", "log", "show", "branch", "rev-parse", "ls-files", "blame", "describe", "tag",
            "shortlog", "remote", "config", "stash", "reflog", "grep", "ls-tree", "cat-file"}


def classify(name: str, args: Dict) -> Optional[Tuple[str, bool]]:
    """(class, dangerous) for tools defined here; None when the tool is not ours."""
    d = EXTRAS.get(name)
    if d is None:
        return None
    if name == "git":
        text = str(args.get("args") or "").strip()
        words = text.split()
        sub = words[0] if words else ""
        from .agent import is_dangerous
        mutating = sub == "stash" and any(w in text for w in ("drop", "clear", "pop", "push", "save")) \
            or sub == "config" and not any(w in text for w in ("--get", "--list", "-l")) \
            or sub == "remote" and any(w in text for w in ("add", "remove", "set-url", "rename", "rm")) \
            or sub == "tag" and len(words) > 1 and not text.startswith(("tag -l", "tag --list"))
        return ("read" if sub in READ_GIT and not mutating else "run"), is_dangerous("git " + text)
    if name == "delete_file":
        return "run", bool(args.get("recursive"))
    return d.perm, False


# ------------------------------------------------------------------- files

@tool("make_dir", "files", "make_dir(path)", "Create a folder (parents too).", {"path": S}, ("path",), "edit", "MakeDir")
def make_dir(t, path: str = "", **_):
    p = t._path(path)
    if p == t.root:
        return True, "프로젝트 폴더", "That is the project folder itself.", {}
    p.mkdir(parents=True, exist_ok=True)
    return True, "폴더 생성: %s" % t.ws.rel(p), "", {}


@tool("move_file", "files", "move_file(src, dest, overwrite=false)", "Move or rename a file/folder inside the project.",
      {"src": S, "dest": S, "overwrite": B}, ("src", "dest"), "edit", "Move")
def move_file(t, src: str = "", dest: str = "", overwrite: bool = False, **_):
    s, d = t._path(src), t._path(dest)
    if not s.exists():
        return False, "없음: %s" % src, "Source does not exist: %s" % src, {}
    if s == t.root:
        return False, "프로젝트 폴더는 옮길 수 없음", "Cannot move the project folder.", {}
    if d.is_dir():
        d = d / s.name
    if d.exists() and not overwrite:
        return False, "이미 있음: %s" % t.ws.rel(d), "Destination exists; pass overwrite=true to replace it.", {}
    if d.is_file():
        t.ws._backup(d)
    if s.is_file():
        t.ws._backup(s)
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return True, "%s → %s" % (t.ws.rel(s), t.ws.rel(d)), "", {}


@tool("copy_file", "files", "copy_file(src, dest)", "Copy a file or folder inside the project.",
      {"src": S, "dest": S}, ("src", "dest"), "edit", "Copy")
def copy_file(t, src: str = "", dest: str = "", **_):
    s, d = t._path(src), t._path(dest)
    if not s.exists():
        return False, "없음: %s" % src, "Source does not exist: %s" % src, {}
    if d.is_dir():
        d = d / s.name
    if d.exists():
        return False, "이미 있음: %s" % t.ws.rel(d), "Destination exists.", {}
    d.parent.mkdir(parents=True, exist_ok=True)
    if s.is_dir():
        shutil.copytree(str(s), str(d), ignore=shutil.ignore_patterns(*IGNORE_DIRS))
    else:
        shutil.copy2(str(s), str(d))
    return True, "복사: %s → %s" % (t.ws.rel(s), t.ws.rel(d)), "", {}


@tool("delete_file", "files", "delete_file(path, recursive=false)", "Delete a file (folders need recursive=true).",
      {"path": S, "recursive": B}, ("path",), "run", "Delete")
def delete_file(t, path: str = "", recursive: bool = False, **_):
    p = t._path(path)
    if p == t.root:
        return False, "프로젝트 폴더는 지울 수 없음", "Refusing to delete the project folder.", {}
    if not p.exists():
        return False, "없음: %s" % path, "Does not exist: %s" % path, {}
    if p.is_dir():
        if not recursive:
            return False, "폴더입니다", "This is a folder: pass recursive=true to delete it with everything inside.", {}
        shutil.rmtree(str(p))
        return True, "폴더 삭제: %s" % t.ws.rel(p), "", {}
    t.ws._backup(p)  # /undo can bring it back
    p.unlink()
    return True, "삭제: %s" % t.ws.rel(p), "", {}


@tool("read_many", "files", "read_many(paths)", "Read several files at once (first 150 lines each).",
      {"paths": A}, ("paths",), "read", "ReadMany")
def read_many(t, paths=None, **_):
    if isinstance(paths, str):
        paths = [x for x in re.split(r"[,\n]", paths) if x.strip()]
    paths = list(paths or [])[:8]
    if not paths:
        return False, "경로 없음", "Give a list of file paths.", {}
    chunks, ok_count = [], 0
    for p in paths:
        ok, summary, out, _x = t.read_file(str(p).strip(), limit=150)
        ok_count += 1 if ok else 0
        chunks.append("=== %s ===\n%s" % (p, out if ok else summary))
    return ok_count > 0, "%d/%d개 읽음" % (ok_count, len(paths)), "\n\n".join(chunks), {}


@tool("tree", "files", 'tree(path=".", depth=3)', "Show the folder structure as a tree.",
      {"path": S, "depth": I}, (), "read", "Tree")
def tree(t, path: str = ".", depth: int = 3, **_):
    base = t._path(path)
    if not base.is_dir():
        return False, "폴더 없음", "Not a folder: %s" % path, {}
    depth = max(1, min(int(depth or 3), 6))
    lines: List[str] = []
    count = [0]

    def walk(d: Path, prefix: str, level: int) -> None:
        try:
            entries = sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError:
            return
        entries = [e for e in entries if e.name not in IGNORE_DIRS and (not e.name.startswith(".") or e.name == ".github")]
        for i, e in enumerate(entries):
            if count[0] >= 300:
                lines.append(prefix + "…")
                return
            last = i == len(entries) - 1
            is_dir = e.is_dir() and not e.is_symlink()
            lines.append(prefix + ("└── " if last else "├── ") + e.name + ("/" if is_dir else ""))
            count[0] += 1
            if is_dir and level < depth:
                walk(e, prefix + ("    " if last else "│   "), level + 1)
    walk(base, "", 1)
    return True, "%d개 항목" % count[0], (t.ws.rel(base) or ".") + "/\n" + "\n".join(lines), {}


# --------------------------------------------------------------------- run

@tool("which", "run", "which(names)", "Is a program installed? (python, node, git, npm, uv, docker …) Empty = common ones.",
      {"names": A}, (), "read", "Which")
def which(t, names=None, **_):
    if isinstance(names, str):
        names = [x for x in re.split(r"[,\s]+", names) if x]
    names = list(names or ["python3", "python", "node", "npm", "npx", "git", "uv", "uvx", "pip", "rg", "docker", "ollama"])[:20]
    lines = []
    for n in names:
        path = shutil.which(str(n))
        ver = ""
        if path and n in ("python", "python3", "node", "git", "npm", "uv", "ollama") and len(names) <= 16:
            try:
                r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                ver = "  (%s)" % ((r.stdout or r.stderr).strip().splitlines() or [""])[0][:60]
            except (OSError, subprocess.SubprocessError):
                pass
        lines.append("%-10s %s%s" % (n, path or "— not found", ver))
    return True, "%d개 확인" % len(lines), "\n".join(lines), {}


_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
          "atan": math.atan, "atan2": math.atan2, "log": math.log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
          "abs": abs, "round": round, "min": min, "max": max, "floor": math.floor, "ceil": math.ceil,
          "radians": math.radians, "degrees": math.degrees, "pow": pow, "hypot": math.hypot}
_CONST = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _calc_eval(node):
    if isinstance(node, ast.Expression):
        return _calc_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        a, b = _calc_eval(node.left), _calc_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(b) > 1000:
            raise ValueError("exponent too large")
        return _BIN[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _calc_eval(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.Name) and node.id in _CONST:
        return _CONST[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        return _FUNCS[node.func.id](*[_calc_eval(a) for a in node.args])
    raise ValueError("unsupported expression")


@tool("calc", "run", "calc(expression)", "Exact arithmetic: + - * / // % ** ( ), sqrt sin cos tan log exp abs round min max floor ceil pi e.",
      {"expression": S}, ("expression",), "read", "Calc")
def calc(t, expression: str = "", **_):
    text = str(expression).replace("^", "**").replace("×", "*").replace("÷", "/")
    if len(text) > 300:
        return False, "너무 김", "Expression too long.", {}
    try:
        val = _calc_eval(ast.parse(text.strip(), mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError) as e:
        return False, "계산 실패", "Cannot calculate %r: %s" % (expression, e), {}
    shown = ("%.10g" % val) if isinstance(val, float) else str(val)
    return True, "= %s" % shown, "%s = %s" % (expression, shown), {}


@tool("python", "run", "python(code | path, args=[], timeout=120)", "Run Python (this machine's interpreter) - a snippet or a file.",
      {"code": S, "path": S, "args": A, "timeout": I}, (), "run", "Python")
def python(t, code: str = "", path: str = "", args=None, timeout: int = 120, **_):
    if not code and not path:
        return False, "코드 없음", "Give code=... or path=...", {}
    from .agent import windows_shell
    if code:
        tmp = t.root / ".lmw" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        f = tmp / "snippet.py"
        f.write_text(code, encoding="utf-8")
        target = ".lmw/tmp/snippet.py"
    else:
        target = t.ws.rel(t._path(path)).replace("\\", "/")
    if isinstance(args, str):
        args = shlex.split(args)
    extra = " ".join(subprocess.list2cmdline([str(a)]) if os.name == "nt" else shlex.quote(str(a)) for a in (args or []))
    exe = sys.executable.replace("\\", "/")
    if os.name == "nt":
        powershell = not windows_shell()[1].startswith("bash")
        cmd = "%s\"%s\" \"%s\" %s" % ("& " if powershell else "", exe, target, extra)
    else:
        cmd = "%s %s %s" % (shlex.quote(exe), shlex.quote(target), extra)
    return t.bash(cmd.strip(), timeout=timeout)


class _Quiet(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".js": "text/javascript", ".mjs": "text/javascript",
                      ".json": "application/json", ".wasm": "application/wasm", ".glb": "model/gltf-binary",
                      ".gltf": "model/gltf+json", ".svg": "image/svg+xml", ".css": "text/css", ".html": "text/html"}

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


_SERVERS: Dict[str, Tuple[ThreadingHTTPServer, int]] = {}


@tool("serve", "run", 'serve(path=".", port=8000, open=false)',
      "Start a local web server for a folder (needed for ES-module pages; stays running). Returns the URL.",
      {"path": S, "port": I, "open": B}, (), "run", "Serve")
def serve(t, path: str = ".", port: int = 8000, open: bool = False, **_):  # noqa: A002
    folder = t._path(path)
    if not folder.is_dir():
        return False, "폴더 없음", "Not a folder: %s" % path, {}
    key = str(folder)
    if key in _SERVERS and _SERVERS[key][0] is not None:
        url = "http://localhost:%d/" % _SERVERS[key][1]
    else:
        srv: Optional[ThreadingHTTPServer] = None
        for p in range(int(port or 8000), int(port or 8000) + 20):
            try:
                srv = ThreadingHTTPServer(("127.0.0.1", p), partial(_Quiet, directory=key))
                break
            except OSError:
                continue
        if srv is None:
            return False, "포트 사용 중", "No free port from %s to %s." % (port, int(port or 8000) + 19), {}
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _SERVERS[key] = (srv, srv.server_address[1])
        url = "http://localhost:%d/" % srv.server_address[1]
    if open:
        webbrowser.open(url)
    return True, url, "Serving %s at %s (only this computer can reach it; stops when lmw exits)." % (t.ws.rel(folder) or ".", url), {}


@tool("open_url", "run", "open_url(target)", "Open a web address or a project file (e.g. index.html) in the default browser.",
      {"target": S}, ("target",), "run", "Open")
def open_url(t, target: str = "", **_):
    tg = str(target).strip()
    if not re.match(r"https?://", tg):
        p = t._path(tg)
        if not p.exists():
            return False, "없음: %s" % tg, "File not found: %s" % tg, {}
        tg = p.resolve().as_uri()
    ok = webbrowser.open(tg)
    return bool(ok), ("열었습니다: " + tg[:80]) if ok else "브라우저를 열지 못함", \
        "Opened %s" % tg if ok else "No browser could be started here; tell the user to open %s." % tg, {}


@tool("download", "run", "download(url, path)", "Download a file from the web into the project (max 25 MB).",
      {"url": S, "path": S}, ("url", "path"), "run", "Download")
def download(t, url: str = "", path: str = "", **_):
    if not re.match(r"https?://", str(url)):
        return False, "http(s) 주소만 가능", "Only http(s) URLs.", {}
    dest = t._path(path)
    if dest.is_dir() or str(path).endswith(("/", "\\")):
        name = os.path.basename(url.split("?")[0].rstrip("/")) or "download"
        dest = dest / name
    cap = 25 * 1024 * 1024
    req = urllib.request.Request(url, headers={"User-Agent": "lmw-cli"})
    try:
        with netutil.urlopen(req, timeout=60) as r:
            data = r.read(cap + 1)
    except Exception as e:
        return False, "다운로드 실패", "Download failed: %s" % e, {}
    if len(data) > cap:
        return False, "25MB 초과", "File is larger than 25 MB.", {}
    if dest.is_file():
        t.ws._backup(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return True, "%s (%.1f KB)" % (t.ws.rel(dest), len(data) / 1024), "Saved %d bytes to %s" % (len(data), t.ws.rel(dest)), {}


@tool("git", "run", "git(args)", 'Run git in the project, e.g. git("status -sb"), git("diff"), git("add -A"), git("commit -m \\"msg\\"").',
      {"args": S}, ("args",), "read", "Git")   # read-only subcommands run freely; classify() asks for the rest
def git(t, args: str = "", **_):
    text = str(args).strip()
    if text.startswith("git "):
        text = text[4:]
    if not text:
        return False, "인자 없음", "Give git arguments, e.g. status -sb", {}
    try:
        argv = shlex.split(text, posix=(os.name != "nt"))
    except ValueError as e:
        return False, "인자 오류", str(e), {}
    argv = [a[1:-1] if len(a) > 1 and a[0] == a[-1] and a[0] in "\"'" else a for a in argv]
    try:
        r = subprocess.run(["git"] + argv, cwd=str(t.root), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
    except FileNotFoundError:
        return False, "git 없음", "git is not installed (winget install Git.Git / brew install git).", {}
    except subprocess.TimeoutExpired:
        return False, "시간 초과", "git took longer than 60 s.", {}
    out = ((r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")).strip()
    from .agent import _clip
    return r.returncode == 0, "exit %d" % r.returncode, _clip(out) or "(no output)", {}


# -------------------------------------------------------------- knowledge

def _words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9+#.]{2,}|[가-힣]{2,}", text.lower())]


def _find_skill(t, name: str):
    n = str(name).strip().lower()
    skills = list(getattr(t, "skills", None) or [])
    for s in skills:
        if s.name.lower() == n:
            return s
    for s in skills:
        if s.name.lower().startswith(n) or n in s.name.lower():
            return s
    return None


@tool("skill_search", "know", "skill_search(query)",
      "Find expert playbooks (design, 3D/three.js, coding, SEO, security …) by ENGLISH keywords; then read one with skill(name).",
      {"query": S}, ("query",), "read", "SkillSearch")
def skill_search(t, query: str = "", **_):
    skills = list(getattr(t, "skills", None) or [])
    qw = set(_words(query))
    if not qw:
        return False, "검색어 없음", "Give English keywords, e.g. 'seo audit' or 'three.js shader'.", {}
    scored = []
    for s in skills:
        score = trigger_score(s.triggers, query) * 2
        name_words = set(re.split(r"[-_ ]+", s.name.lower()))
        score += 4 * len(qw & name_words)
        score += len(qw & set(_words(s.description)))
        if score:
            scored.append((score, s.library, s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        return True, "없음", "No skill matches. Try other (English) keywords.", {}
    lines = ["%s%s — %s" % (s.name, " [library:%s]" % s.source if lib else "", s.description[:130]) for _sc, lib, s in scored[:8]]
    return True, "%d개 후보" % len(lines), "\n".join(lines) + '\n\nRead one with skill("<name>").', {}


@tool("skill", "know", 'skill(name, topic="")',
      "Read a skill playbook (rules + examples). topic = one of its reference names for deeper material.",
      {"name": S, "topic": S}, ("name",), "read", "Skill")
def skill(t, name: str = "", topic: str = "", **_):
    s = _find_skill(t, name)
    if s is None:
        sug = [x.name for x in (getattr(t, "skills", None) or []) if str(name).lower()[:4] and str(name).lower()[:4] in x.name.lower()][:8]
        return False, "스킬 없음: %s" % name, "No skill %r.%s Use skill_search(query)." % (name, " Similar: " + ", ".join(sug) + "." if sug else ""), {}
    refs = {r.name.lower(): r for r in s.references}
    if topic:
        r = refs.get(str(topic).lower()) or next((v for k, v in refs.items() if str(topic).lower() in k), None)
        if r is None:
            return False, "자료 없음: %s" % topic, "%s has no reference %r. Available: %s" % (s.name, topic, ", ".join(refs) or "none"), {}
        return True, "%s/%s (%d자)" % (s.name, r.name, len(r.body)), r.body, {}
    body = s.body
    foot = ""
    if refs:
        foot = '\n\n[deeper material: ' + ", ".join('skill("%s", "%s")' % (s.name, k) for k in refs) + "]"
    if s.checklist:
        foot += '\n[review checklist available]'
    return True, "%s (%d자)" % (s.name, len(body)), body + foot, {}


_STATUS = {"done": "☒", "doing": "◐", "pending": "☐"}


def _parse_todo(item) -> Tuple[str, str]:
    if isinstance(item, dict):
        txt = str(item.get("text") or item.get("title") or item.get("task") or "")
        st = str(item.get("status") or "pending").lower()
        return txt, st if st in _STATUS else ("done" if st in ("completed", "complete", "x") else "pending")
    txt = str(item).strip()
    m = re.match(r"^\[(.)\]\s*(.*)$", txt)
    if m:
        mark = m.group(1).lower()
        return m.group(2), "done" if mark == "x" else ("doing" if mark in "~>-*" else "pending")
    return txt, "pending"


@tool("todo", "know", "todo(items)", 'Keep a visible checklist for multi-step work: items like ["[x] read", "[~] build", "[ ] test"]. Send the whole list each time.',
      {"items": A}, ("items",), "read", "Todo")
def todo(t, items=None, **_):
    if isinstance(items, str):
        items = [x for x in items.splitlines() if x.strip()]
    parsed = [_parse_todo(i) for i in (items or [])][:30]
    parsed = [(a, b) for a, b in parsed if a]
    t.todos = [{"text": a, "status": b} for a, b in parsed]
    from .events import emit
    emit("todo", items=t.todos)
    done = sum(1 for _a, b in parsed if b == "done")
    return True, "%d/%d 완료" % (done, len(parsed)), "\n".join("%s %s" % (_STATUS[b], a) for a, b in parsed) or "(empty)", {}


def _memory_file(t) -> Path:
    return t.root / ".lmw" / "memory.md"


@tool("remember", "know", "remember(note)", "Save a short fact about this project for later sessions (decisions, commands, gotchas).",
      {"note": S}, ("note",), "read", "Remember")
def remember(t, note: str = "", **_):
    text = " ".join(str(note).split())
    if not text:
        return False, "내용 없음", "Give a note.", {}
    f = _memory_file(t)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write("- %s %s\n" % (time.strftime("%Y-%m-%d"), text[:500]))
    return True, "기억함", "Saved to .lmw/memory.md", {}


@tool("recall", "know", 'recall(query="")', "Read the project notes saved with remember (filtered by words in query).",
      {"query": S}, (), "read", "Recall")
def recall(t, query: str = "", **_):
    f = _memory_file(t)
    if not f.is_file():
        return True, "메모 없음", "No notes yet.", {}
    lines = [l for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    qw = _words(query)
    if qw:
        lines = [l for l in lines if any(w in l.lower() for w in qw)]
    return True, "%d개" % len(lines[-30:]), "\n".join(lines[-30:]) or "No matching notes.", {}


@tool("ask_user", "know", "ask_user(question)", "Ask the user ONE short question when a decision is really theirs (not for permission).",
      {"question": S}, ("question",), "read", "Ask")
def ask_user(t, question: str = "", **_):
    cb = getattr(t, "ask_cb", None)
    if cb is None:
        return True, "(답변 없음)", "(The user cannot be asked now - choose the most reasonable option yourself.)", {}
    answer = (cb(str(question)) or "").strip()
    return True, "답변: %s" % answer[:60], answer or "(no preference - decide yourself)", {}


@tool("agent", "know", "agent(name, task)",
      'Hand a focused job to a specialist sub-agent (e.g. code-reviewer, architect, debugger). agent("list") shows them.',
      {"name": S, "task": S}, ("name", "task"), "read", "Agent")
def agent(t, name: str = "", task: str = "", **_):
    cb = getattr(t, "agent_cb", None)
    if cb is None:
        return False, "하위 에이전트 사용 불가", "Sub-agents are not available here.", {}
    return cb(str(name), str(task))


# ---------------------------------------------------------- prompt pieces

def _visible(d: ToolDef, include_agent: bool, read_only: bool) -> bool:
    return (include_agent or d.name != "agent") and (not read_only or d.perm == "read")


def docs(include_agent: bool = True, read_only: bool = False) -> str:
    """Compact catalog for the system prompt (one line per group). read_only hides tools that change things."""
    out = ["# More tools (same <tool_call> format)"]
    for gid, gname in GROUPS:
        items = [d.sig for d in EXTRAS.values() if d.group == gid and _visible(d, include_agent, read_only)]
        if items:
            out.append("%s: %s" % (gname, " · ".join(items)))
    out.append("Prefer these over shell tricks: make_dir/move_file/copy_file instead of mkdir/mv/cp, tree/read_many to explore, "
               "serve + open_url to show a web page, skill/skill_search for expert playbooks, todo for multi-step plans.")
    return "\n".join(out)


def schemas(include_agent: bool = True, read_only: bool = False) -> List[Dict]:
    out = []
    for d in EXTRAS.values():
        if not _visible(d, include_agent, read_only):
            continue
        out.append({"type": "function", "function": {"name": d.name, "description": d.desc, "parameters": {
            "type": "object", "properties": d.props, "required": d.required}}})
    return out


def overview(cfg, root) -> List[str]:
    """Everything the agent can use, one line each (for /tools and `lmw tools`)."""
    from . import agents as agentlib, mcp, usercmds
    from .skills import all_skills
    core = ["read_file", "write_file", "edit_file", "list_dir", "glob", "grep", "bash", "web_search", "web_fetch"]
    skills = all_skills(cfg.resolved_skills_dir())
    own = [s for s in skills if not s.library]
    m = mcp.manager(str(root))
    return [
        "기본 도구 %d개:  %s" % (len(core), ", ".join(core)),
        "추가 도구 %d개:  %s" % (len(EXTRAS), ", ".join(EXTRAS)),
        "MCP 서버 %d개 · 도구 %d개  (mcp list)" % (len(m.servers), len(m.tool_list())),
        "하위 에이전트 %d개  (agents list)" % len(agentlib.load_agents()),
        "스킬 %d개 (내장) + 설치한 외부 스킬 %d개  (skills list)" % (len(own), len(skills) - len(own)),
        "가져온 슬래시 명령 %d개  (cmds list)" % len(usercmds.load()),
    ]
