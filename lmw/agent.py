"""The LMW coding agent: a tool-using loop for any local model (Claude-Code style).

Tools: read_file, write_file, edit_file, list_dir, glob, grep, bash.
Tool-call format: <tool_call>{"name": ..., "arguments": {...}}</tool_call> — the format
Qwen2.5/Qwen3, Hermes and many other open models are trained on, and easy for any model
to imitate. Search uses ripgrep (the open-source tool Claude Code also uses) when installed.

Effort routing keeps simple things fast:
  chat   - greetings / small talk -> one short reply, no tools, no thinking
  agent  - normal requests -> tool loop (thinking only when the task needs it)
  deep   - big "build me X" requests or effort=high -> the 8-phase pipeline
"""

from __future__ import annotations

import difflib
import fnmatch
import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import ui
from .client import ChatClient, ContextRefit, ModelError
from .config import Config
from .events import TOOL_LABELS, emit
from .parse import apply_edits, Edit
from .skills import load_skills, select_skills
from .stats import STATS, fmt_tokens
from .textutil import detect_language, estimate_tokens, truncate_to_tokens
from .workspace import IGNORE_DIRS, UnsafePathError, Workspace

MODES = ("ask", "auto-edit", "full")
EFFORTS = ("auto", "low", "medium", "high")
MAX_STEPS = 40
MAX_OUTPUT = 12000


class Interrupted(Exception):
    pass


# ------------------------------------------------------------------ routing

_SMALLTALK = re.compile(
    r"^\s*(안녕|하이|ㅎㅇ|반가워|고마워|감사|땡큐|수고|잘\s*자|좋은\s*(아침|하루)|hi|hello|hey|yo|thanks?|thank you|"
    r"good (morning|night)|ok|okay|ㅇㅋ|오케이|넵|네|응|ㅋ+|ㅎ+)[\s!.?~ㅎㅋ^]*$", re.I)
_TECH = re.compile(r"(파일|폴더|코드|함수|클래스|프로젝트|에러|오류|버그|만들|고쳐|수정|실행|설치|빌드|테스트|배포|"
                   r"요약|읽어|보여|찾아|열어|분석|설명해|readme|summar|"
                   r"검색|찾아봐|알아봐|뉴스|최신|요즘|오늘|날씨|가격|주가|환율|버전|search|latest|news|price|weather|https?://|www\.|"
                   r"file|code|error|bug|build|run|fix|install|test|deploy|\.\w{1,5}\b|/|\\)", re.I)
_BUILD_VERB = re.compile(r"(만들어|만들자|제작|개발해|구현해|짜줘|build|create|make|develop)", re.I)
_BUILD_NOUN = re.compile(r"(웹사이트|홈페이지|사이트|웹앱|앱|어플|게임|랜딩|대시보드|쇼핑몰|포트폴리오|프로젝트|서비스|"
                         r"website|web app|app|game|landing|dashboard|portfolio|project)", re.I)


_CODE_TASK = re.compile(
    r"(코드|코딩|함수|클래스|메서드|모듈|스크립트|프로그램|구현|작성해|짜줘|짜 줘|만들어|고쳐|수정해|바꿔|추가해|삭제해|리팩|"
    r"버그|에러|오류|디버그|테스트 (작성|추가)|최적화|마이그레이션|"
    r"implement|write|refactor|fix|debug|add|create|build|optimi[sz]e|migrate|code|function|class|script)", re.I)


def wants_thinking(text: str, effort: str) -> bool:
    """Only real code work thinks; questions and simple requests answer directly (effort=auto)."""
    if effort == "high":
        return True
    if effort == "low":
        return False
    return bool(_CODE_TASK.search(text))


def route(text: str, effort: str) -> str:
    t = text.strip()
    if _SMALLTALK.match(t) or (len(t) <= 12 and not _TECH.search(t)):
        return "chat"
    return "agent"  # the step-by-step plan mode runs only when asked: /plan (/계획)


# -------------------------------------------------------------- permissions

_DANGER = re.compile(
    r"(\brm\s+(-\w*\s+)*-\w*[rf]|\brmdir\s+/s|\bdel\s+/[sq]|\bformat\s+[a-z]:|\bmkfs|\bdd\s+if=|\bshutdown\b|\breboot\b|"
    r"git\s+push\s+.*(--force|-f\b)|git\s+reset\s+--hard|git\s+clean\s+-\w*f|chmod\s+-R\s+777|"
    r"curl[^|]*\|\s*(sudo\s+)?(ba)?sh|wget[^|]*\|\s*(sudo\s+)?(ba)?sh|Remove-Item\s+.*-Recurse|\bsudo\b|:\(\)\s*\{)", re.I)


def is_dangerous(command: str) -> bool:
    return bool(_DANGER.search(command or ""))


class Permissions:
    """ask: reads free, ask for edits & commands | auto-edit: edits free, ask for commands | full: all free.
    Dangerous commands are always asked, in every mode."""

    def __init__(self, mode: str = "ask"):
        self.mode = mode if mode in MODES else "ask"
        self.always: set = set()  # "edit" or "bash:<prefix>"

    @staticmethod
    def bash_key(command: str) -> str:
        words = command.strip().split()
        return "bash:" + " ".join(words[:2]) if words else "bash:"

    def needs_ask(self, tool: str, args: Dict) -> Tuple[bool, bool]:
        """(ask?, dangerous?)"""
        if tool in ("read_file", "list_dir", "glob", "grep", "web_search", "web_fetch"):
            return False, False
        if tool in ("write_file", "edit_file"):
            return (self.mode == "ask" and "edit" not in self.always), False
        if tool == "bash":
            cmd = str(args.get("command", ""))
            if is_dangerous(cmd):
                return True, True
            if self.mode == "full" or self.bash_key(cmd) in self.always:
                return False, False
            return True, False
        return self.mode != "full", False

    def remember(self, tool: str, args: Dict) -> None:
        self.always.add("edit" if tool in ("write_file", "edit_file") else self.bash_key(str(args.get("command", ""))))


# -------------------------------------------------------------------- tools

TOOL_DOCS = """- read_file(path, offset=1, limit=400): read a text file; lines are numbered.
- write_file(path, content): create or fully overwrite a file with the COMPLETE content.
- edit_file(path, old_string, new_string, replace_all=false): replace exact text in a file. old_string must match the file exactly (copy it from read_file output, without line numbers) and be unique unless replace_all.
- list_dir(path="."): list files and folders.
- glob(pattern): find files by name, e.g. "**/*.py", "src/**/*.css".
- grep(pattern, path=".", glob=null, ignore_case=false): search file contents with a regex; returns file:line: text.
- bash(command, timeout=120): run a shell command in the project folder (%s). Use for tests, builds, git, package managers.
- web_search(query, count=8): search the internet; returns titles, URLs and snippets. Use for current information, news, prices, docs, error messages, library versions — anything you are not sure about or that may have changed.
- web_fetch(url): read a web page as plain text (use after web_search to read a result, or for a URL the user gave)."""


def _fn(name: str, desc: str, props: Dict, required: List[str]) -> Dict:
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required}}}


_S, _I, _B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
TOOL_SCHEMAS = [
    _fn("read_file", "Read a text file (lines are numbered).", {"path": _S, "offset": _I, "limit": _I}, ["path"]),
    _fn("write_file", "Create or fully overwrite a file with the COMPLETE content.", {"path": _S, "content": _S}, ["path", "content"]),
    _fn("edit_file", "Replace exact text in a file (old_string must match exactly and be unique unless replace_all).",
        {"path": _S, "old_string": _S, "new_string": _S, "replace_all": _B}, ["path", "old_string", "new_string"]),
    _fn("list_dir", "List files and folders.", {"path": _S}, []),
    _fn("glob", "Find files by name pattern, e.g. **/*.py", {"pattern": _S}, ["pattern"]),
    _fn("grep", "Search file contents with a regex.", {"pattern": _S, "path": _S, "glob": _S, "ignore_case": _B}, ["pattern"]),
    _fn("bash", "Run a shell command in the project folder.", {"command": _S, "timeout": _I}, ["command"]),
    _fn("web_search", "Search the internet.", {"query": _S, "count": _I}, ["query"]),
    _fn("web_fetch", "Read a web page as text.", {"url": _S}, ["url"]),
]

# "I can't create files" / code pasted instead of saved: the model forgot it has tools
_REFUSAL = re.compile(r"(직접\s*(만들|생성|작성|수정|저장)[^.\n]{0,20}(수\s*(는|가|도)?\s*없|못)|"
                      r"파일을?\s*(직접\s*)?(만들|생성|저장|수정)[^.\n]{0,15}(수\s*(는|가|도)?\s*없|못)|"
                      r"접근할\s*수\s*없|can(?:no|')t\s+(create|write|access|modify|edit)|unable to (create|write|access)|"
                      r"as an ai|i don't have (access|the ability))", re.I)
# "would you like to try…", "run this yourself" — the agent should do it, not the user
_HANDBACK = re.compile(r"(시도해\s*보시겠|해\s*보시겠습니까|실행해\s*보세요|직접\s*(실행|입력|수정|변경|확인)해\s*(보세요|주세요)|"
                       r"다음과\s*같이\s*(변경|수정|실행)|해\s*보시기\s*바랍|사용할\s*수\s*있습니다\.?\s*$|"
                       r"would you like (me )?to|you can (run|try|use)|try (running|the following)|please run)", re.I | re.M)
# "I'll now create…" with no tool call: it announced the next step but stopped
_INTENT = re.compile(r"(하겠습니다|해\s*보겠습니다|진행하겠|시작하겠|만들겠|작성하겠|생성하겠|설정하겠|확인하겠|"
                     r"\b(let me|i will|i'll|next,? i|now i('ll| will)|let's)\b)", re.I)
# requests that are only done when files exist
_MAKE = re.compile(r"(만들어|만들자|생성해|작성해|구현해|짜줘|추가해|수정해|고쳐|바꿔|create|build|make|write|implement|add|fix)", re.I)
_CODE_BLOCK = re.compile(r"```[\w+-]*\n[\s\S]{200,}?```")


def windows_shell() -> Tuple[List[str], str]:
    """(argv prefix, name) of the shell used for the bash tool on Windows."""
    for c in (os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Git", "bin", "bash.exe"),
              os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "bin", "bash.exe")):
        if c and os.path.isfile(c):
            return [c, "-lc"], "bash (Git Bash: grep, ls, cat, rm, … work)"
    ps = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
    return [ps, "-NoProfile", "-NonInteractive", "-Command"], \
        "PowerShell (no grep/cat/rm -rf: use Select-String, Get-Content, Remove-Item, or the grep/glob/read_file tools)"


def shell_name() -> str:
    return windows_shell()[1] if os.name == "nt" else "sh"


_WIN_HINT = ("\n[hint] This is Windows. Use the grep / glob / read_file / list_dir tools for searching and reading, "
             "and PowerShell syntax for commands (Select-String, Get-ChildItem, Get-Content). Fix the command and continue.")


class Tools:
    def __init__(self, root: Path, check_stop: Callable[[], None]):
        self.ws = Workspace(root)
        self.root = self.ws.root
        self.check_stop = check_stop
        self.rg = shutil.which("rg")

    def _path(self, p: str) -> Path:
        p = str(p or "").strip().strip('"').strip("'")
        if p in ("", ".", "./", ".\\"):
            return self.root
        q = Path(p).expanduser()
        if q.is_absolute():  # models often pass absolute paths; allow them inside the project only
            try:
                p = q.resolve().relative_to(self.root).as_posix() or "."
            except ValueError:
                raise UnsafePathError("path is outside the project folder: %s" % p)
            if p == ".":
                return self.root
        return self.ws.resolve(p)

    # each returns (ok, summary, output, extra)
    def read_file(self, path: str, offset: int = 1, limit: int = 400, **_):
        p = self._path(path)
        if not p.is_file():
            return False, "파일 없음: %s" % path, "File not found: %s" % path, {}
        text = self.ws.read(self.ws.rel(p))
        if text is None:
            return False, "읽을 수 없는 파일", "Binary or too large file: %s" % path, {}
        lines = text.splitlines()
        offset = max(1, int(offset or 1))
        limit = max(1, min(int(limit or 400), 2000))
        chunk = lines[offset - 1: offset - 1 + limit]
        out = "\n".join("%5d\t%s" % (i, l) for i, l in enumerate(chunk, offset))
        more = len(lines) - (offset - 1 + len(chunk))
        if more > 0:
            out += "\n... (%d more lines; use offset=%d)" % (more, offset + len(chunk))
        return True, "%d줄 읽음" % len(chunk), out, {}

    def write_file(self, path: str, content: str = "", **_):
        rel = self.ws.rel(self._path(path))
        old = self.ws.read(rel) if (self.root / rel).exists() else None
        self.ws.write(rel, content if content.endswith("\n") or not content else content + "\n")
        n = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        diff = _diff(old or "", content, rel) if old is not None else ""
        return True, ("%d줄 작성 (새 파일)" % n if old is None else "%d줄로 덮어씀" % n), "", {"diff": diff}

    def edit_file(self, path: str, old_string: str = "", new_string: str = "", replace_all: bool = False, **_):
        rel = self.ws.rel(self._path(path))
        cur = self.ws.read(rel)
        if cur is None:
            return False, "파일 없음: %s" % path, "File not found (use write_file to create it): %s" % path, {}
        if not old_string:
            return False, "old_string 비어 있음", "old_string must not be empty", {}
        count = cur.count(old_string)
        if count > 1 and not replace_all:
            return False, "일치하는 곳이 %d군데" % count, ("old_string matches %d places; add more surrounding context "
                                                        "or set replace_all=true" % count), {}
        if count >= 1:
            new = cur.replace(old_string, new_string) if replace_all else cur.replace(old_string, new_string, 1)
        else:
            new, failed = apply_edits(cur, [Edit(old_string, new_string)])  # whitespace-tolerant fallback
            if failed:
                return False, "old_string 을 찾지 못함", ("old_string was not found in %s. Read the file again and copy "
                                                        "the exact text." % path), {}
        self.ws.write(rel, new)
        d = _diff(cur, new, rel)
        plus = sum(1 for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
        minus = sum(1 for l in d.splitlines() if l.startswith("-") and not l.startswith("---"))
        return True, "+%d −%d" % (plus, minus), "", {"diff": d}

    def preview(self, name: str, args: Dict) -> str:
        """Diff of a proposed write/edit (nothing is written) — shown when asking permission."""
        try:
            rel = self.ws.rel(self._path(args.get("path", "")))
            cur = self.ws.read(rel) if (self.root / rel).exists() else None
            if name == "write_file":
                return _diff(cur or "", str(args.get("content", "")), rel)
            if name == "edit_file" and cur is not None:
                old, new = str(args.get("old_string", "")), str(args.get("new_string", ""))
                if old and old in cur:
                    return _diff(cur, cur.replace(old, new) if args.get("replace_all") else cur.replace(old, new, 1), rel)
        except Exception:
            pass
        return ""

    def list_dir(self, path: str = ".", **_):
        p = self._path(path)
        if not p.is_dir():
            return False, "폴더 없음", "Not a directory: %s" % path, {}
        items = []
        for c in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if c.name in IGNORE_DIRS:
                continue
            items.append(c.name + ("/" if c.is_dir() else ""))
        return True, "%d개 항목" % len(items), "\n".join(items[:500]) or "(empty)", {}

    def glob(self, pattern: str = "**/*", **_):
        out = []
        for f in self.ws.iter_files():
            rel = self.ws.rel(f)
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, pattern.replace("**/", "")) \
                    or fnmatch.fnmatch(f.name, pattern):
                out.append(rel)
            if len(out) >= 300:
                break
        return True, "%d개 파일" % len(out), "\n".join(out) or "(no matches)", {}

    def grep(self, pattern: str = "", path: str = ".", glob: Optional[str] = None, ignore_case: bool = False, **_):
        base = self._path(path)
        if self.rg:
            cmd = [self.rg, "-n", "--no-heading", "--color", "never", "-m", "50", "--max-columns", "300"]
            if ignore_case:
                cmd.append("-i")
            if glob:
                cmd += ["-g", glob]
            cmd += ["-e", pattern, str(base)]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            lines = [l.replace(str(self.root) + os.sep, "") for l in r.stdout.splitlines()][:300]
        else:
            try:
                rx = re.compile(pattern, re.I if ignore_case else 0)
            except re.error as e:
                return False, "잘못된 정규식", str(e), {}
            lines = []
            files = [base] if base.is_file() else self.ws.iter_files()
            for f in files:
                rel = self.ws.rel(f)
                if base.is_dir() and not str(f).startswith(str(base)):
                    continue
                if glob and not fnmatch.fnmatch(rel, glob) and not fnmatch.fnmatch(f.name, glob):
                    continue
                text = self.ws.read(rel)
                if text is None:
                    continue
                for i, l in enumerate(text.splitlines(), 1):
                    if rx.search(l):
                        lines.append("%s:%d:%s" % (rel, i, l[:300]))
                if len(lines) >= 300:
                    break
        return True, "%d개 일치" % len(lines), "\n".join(lines) or "(no matches)", {}

    def bash(self, command: str = "", timeout: int = 120, **_):
        if not command.strip():
            return False, "명령 없음", "empty command", {}
        timeout = max(1, min(int(timeout or 120), 1800))
        try:
            if os.name == "nt":
                argv = windows_shell()[0] + [command]
                proc = subprocess.Popen(argv, cwd=str(self.root), stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            else:
                proc = subprocess.Popen(command, shell=True, cwd=str(self.root), stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        except OSError as e:
            return False, "실행 실패", str(e), {}
        out: List[str] = []
        reader = threading.Thread(target=lambda: out.extend(proc.stdout), daemon=True)  # type: ignore[arg-type]
        reader.start()
        start = time.time()
        while proc.poll() is None:
            try:
                self.check_stop()
            except Interrupted:
                proc.kill()
                raise
            if time.time() - start > timeout:
                proc.kill()
                reader.join(2)
                return False, "시간 초과 (%ds)" % timeout, _clip("".join(out)) + "\n[timed out]", {}
            time.sleep(0.1)
        reader.join(5)
        text = _clip("".join(out))
        if proc.returncode != 0 and os.name == "nt" and re.search(
                r"not recognized|인식되지|CommandNotFound|command not found|is not recognized", text, re.I):
            text += _WIN_HINT  # e.g. grep in cmd: tell the model how to do it here instead of giving up
        return proc.returncode == 0, "exit %d" % proc.returncode, text or "(no output)", {}

    searxng = ""  # optional SearXNG URL from the config

    def web_search(self, query: str = "", count: int = 8, **_):
        from . import web
        if not str(query).strip():
            return False, "검색어 없음", "query must not be empty", {}
        res = web.search(str(query), count, self.searxng)
        if not res:
            return True, "결과 없음", "No results.", {}
        out = "\n\n".join("%d. %s\n   %s\n   %s" % (i, r["title"], r["url"], r["snippet"][:300])
                           for i, r in enumerate(res, 1))
        return True, "%d개 결과" % len(res), out, {"results": res[:8]}

    def web_fetch(self, url: str = "", **_):
        from . import web
        if not str(url).strip():
            return False, "URL 없음", "url must not be empty", {}
        page = web.fetch_text(str(url))
        return True, "%s (%d자)" % ((page["title"] or page["url"])[:60], len(page["text"])), \
            "# %s\n%s\n\n%s" % (page["title"], page["url"], page["text"]), {}

    def run(self, name: str, args: Dict):
        fn = getattr(self, name, None) if name in TOOL_LABELS else None
        if fn is None:
            return False, "알 수 없는 도구: %s" % name, "Unknown tool %r. Available: %s" % (name, ", ".join(TOOL_LABELS)), {}
        try:
            return fn(**args)
        except UnsafePathError as e:
            return False, "프로젝트 밖 경로는 사용할 수 없음", str(e), {}
        except TypeError as e:
            return False, "잘못된 인자", "Bad arguments for %s: %s" % (name, e), {}
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return False, "실패: %s" % e, str(e), {}


def _clip(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n\n[... %d chars omitted ...]\n\n" % (len(text) - limit) + text[-half:]


def _diff(old: str, new: str, path: str) -> str:
    return "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), "a/" + path, "b/" + path, lineterm="", n=2))


def tool_title(name: str, args: Dict) -> str:
    label = TOOL_LABELS.get(name, name)
    if name == "bash":
        arg = str(args.get("command", ""))
    elif name == "web_search":
        arg = str(args.get("query", ""))
    elif name == "web_fetch":
        arg = str(args.get("url", ""))
    elif name in ("glob", "grep"):
        arg = str(args.get("pattern", ""))
        if name == "grep" and args.get("path") not in (None, "", "."):
            arg += " in " + str(args["path"])
    else:
        arg = str(args.get("path", "."))
    arg = arg.replace("\n", " ")
    return "%s(%s)" % (label, arg[:100] + ("…" if len(arg) > 100 else ""))


# ------------------------------------------------------------------ parsing

_CALL = re.compile(r"<tool_call>\s*(.*?)\s*(</tool_call>|$)", re.S)
_FENCED = re.compile(r"```(?:json|tool_call)?\s*(\{\s*\"name\"\s*:.*?\})\s*```", re.S)
_THINK = re.compile(r"<think>(.*?)(</think>|$)", re.S)


def split_thinking(text: str) -> Tuple[str, str]:
    thoughts = [m.group(1).strip() for m in _THINK.finditer(text)]
    visible = _THINK.sub("", text)
    if "</think>" in visible:  # an unopened closing tag: everything before it was thinking
        before, _, visible = visible.partition("</think>")
        thoughts.insert(0, before.strip())
    return "\n\n".join(t for t in thoughts if t), visible.strip()


def _loads(raw: str) -> Optional[Dict]:
    raw = raw.strip().strip("`")
    for attempt in (raw, re.sub(r",\s*([}\]])", r"\1", raw)):
        try:
            v = json.loads(attempt)
            return v if isinstance(v, dict) else None
        except ValueError:
            continue
    # first balanced {...}
    depth, start = 0, raw.find("{")
    if start < 0:
        return None
    for i in range(start, len(raw)):
        depth += raw[i] == "{"
        depth -= raw[i] == "}"
        if depth == 0:
            try:
                return json.loads(raw[start:i + 1])
            except ValueError:
                return None
    return None


def parse_tool_calls(text: str) -> Tuple[List[Dict], str]:
    """Returns ([{name, arguments}], text-without-calls)."""
    calls = []
    found = list(_CALL.finditer(text))
    if not found:
        found = list(_FENCED.finditer(text))
    for m in found:
        v = _loads(m.group(1))
        if not v:
            continue
        name = v.get("name") or v.get("tool") or v.get("function")
        args = v.get("arguments") or v.get("args") or v.get("parameters") or v.get("input") or {}
        if isinstance(args, str):
            args = _loads(args) or {}
        if name:
            calls.append({"name": str(name), "arguments": args if isinstance(args, dict) else {}})
    prose = _CALL.sub("", text) if _CALL.search(text) else (_FENCED.sub("", text) if calls else text)
    return calls, prose.strip()


# -------------------------------------------------------------------- agent

SYSTEM = """You are LMW, an expert coding agent working directly on the user's computer.
Project folder: {cwd}   OS: {os}   Date: {date}

You read, search and change files and run commands by calling tools. You CAN create, edit and delete files and
run programs on this computer — never say you cannot; do the work with the tools instead of pasting code.

# Calling tools
Write each tool call exactly like this (valid JSON inside the tags):
<tool_call>
{{"name": "read_file", "arguments": {{"path": "src/app.py"}}}}
</tool_call>
You may call several tools in one reply. After the calls STOP; results arrive in <tool_result> blocks and you continue.
When the work is finished, or for conversation, reply WITHOUT any tool call.

# Tools
{tools}

# How to work
- Understand first: search (grep/glob) and read the relevant files before changing anything. Never guess file contents.
- Small change: edit_file with an exact, unique old_string. New file or full rewrite: write_file with the complete content. No placeholders like "..." or "rest of code".
- Keep the user's request as the goal; do exactly what was asked, completely. Finish it yourself: never end by asking
  the user to run commands, try something or make changes — you run, check and fix things with the tools.
- When a command fails, find out why and try another way (other command, the grep/glob/read_file tools) — don't give up.
- Verify: run the project's tests/build/linter when they exist, or re-read what you changed. Fix failures before finishing.
- The user is asked automatically before edits and commands; never ask in text for permission to proceed.
- Only tell the user things that matter (a decision, a problem, a question you cannot answer yourself). No running commentary.
- Finish with a short summary of what changed and how to run/verify it.
- Reply in {language}. Code, identifiers and file names in English.
{effort}
# Project files
{tree}
{skills}"""

EFFORT_RULES = {
    "none": "- Answer directly. Do NOT think out loud and do not write <think> blocks; use tools only if you must look something up.",
    "low": "- Be quick: minimal reasoning, as few tool calls as possible. Do not write <think> blocks.",
    "medium": "- Think inside <think>...</think> only when the task is genuinely complex; keep it short. Simple requests: act or answer immediately.",
    "high": "- Before acting, plan inside <think>...</think>: goal, steps, risks. Before finishing, review your result against the request.",
}

CHAT_SYSTEM = ("You are LMW, a friendly coding assistant. This is small talk: reply in one or two short, natural "
               "sentences in {language}. Do not think out loud, do not use tools.")


class Agent:
    def __init__(self, cfg: Config, root: Path, client: ChatClient,
                 ask_permission: Callable[[Dict], str], perms: Permissions,
                 stop: threading.Event):
        self.cfg = cfg
        self.root = root.resolve()
        self.client = client
        self.ask_permission = ask_permission  # (permission event) -> "allow" | "always" | "deny"
        self.perms = perms
        self.stop = stop
        self.tools = Tools(self.root, self.check_stop)
        self.tools.searxng = getattr(cfg, "search_url", "")
        self.history: List[Dict[str, str]] = []
        self._skills = load_skills(cfg.resolved_skills_dir())

    def check_stop(self) -> None:
        if self.stop.is_set():
            raise Interrupted()

    # ---------------------------------------------------------------- prompts
    def _system(self, user_text: str, effort: str, readonly: bool) -> str:
        tree = self.tools.ws.tree(max_entries=120)
        picked = [s for s in select_skills(self._skills, user_text, self.cfg.skills, self.cfg.exclude_skills) if not s.always]
        skills = ""
        if picked and effort != "low":
            budget = max(600, self._budget() // 6)
            body = "\n\n".join("## %s\n%s" % (s.name, s.body) for s in picked)
            skills = "\n# Expert guidance\n" + truncate_to_tokens(body, budget)
        tools = TOOL_DOCS % shell_name()
        if readonly:
            tools = "\n".join(l for l in tools.splitlines() if not l.startswith(("- write_file", "- edit_file", "- bash")))
        return SYSTEM.format(cwd=self.root, os="%s %s" % (platform.system(), platform.release()),
                             date=time.strftime("%Y-%m-%d"), tools=tools,
                             language=detect_language(user_text), effort=EFFORT_RULES.get(effort, EFFORT_RULES["medium"]),
                             tree=tree, skills=skills)

    # ------------------------------------------------------- auto-compaction
    _readonly = False
    COMPACT_AT = 0.8  # summarize older messages when the conversation fills 80% of the context

    def _history_tokens(self) -> int:
        return sum(estimate_tokens(m["content"]) for m in self.history)

    def _budget(self) -> int:
        """Prompt budget: what the config allows AND what really fits on the server (learned token ratio)."""
        pb = getattr(self.client, "prompt_budget", None)
        return min(self.cfg.input_budget(), pb()) if callable(pb) else self.cfg.input_budget()

    interject = None  # set by the shell: () -> [lines the user added while this request runs]

    def _interjections(self) -> List[str]:
        try:
            return list(self.interject() or []) if self.interject else []
        except Exception:
            return []

    def _add_interjection(self, t: str) -> None:
        emit("user", text=t, interject=True)
        self.history.append({"role": "user", "content": "[The user added while you were working — handle this too, "
                                                        "in order, after what you were doing]\n" + t})

    def maybe_compact(self, system: str) -> None:
        budget = self._budget() - estimate_tokens(system)
        if self._history_tokens() > self.COMPACT_AT * budget and len(self.history) > 4:
            self.compact(budget)

    def compact(self, budget: Optional[int] = None, manual: bool = False) -> bool:
        """Replace older messages with a model-written summary, keep the recent ones word for word."""
        budget = budget or self._budget()
        before = self._history_tokens()
        # keep the newest messages (about a third of the budget), starting at a real user message
        keep, used = len(self.history), 0
        while keep > 0 and used + estimate_tokens(self.history[keep - 1]["content"]) < budget * 0.35:
            keep -= 1
            used += estimate_tokens(self.history[keep]["content"])
        while keep < len(self.history) and not (self.history[keep]["role"] == "user"
                                                and not self.history[keep]["content"].startswith("<tool_result")):
            keep += 1
        if keep >= len(self.history):  # the last request alone is huge: keep only the latest request
            keep = max(i for i, m in enumerate(self.history) if m["role"] == "user")
        head, tail = self.history[:keep], self.history[keep:]
        if not head:
            return False
        lines, room = [], int(budget * 0.6) * 3  # characters of transcript the summarizer may read
        for m in head:
            c = str(m["content"])
            if c.startswith("<tool_result"):
                c = c[:600] + ("…" if len(c) > 600 else "")
            else:
                c = c[:3000] + ("…" if len(c) > 3000 else "")
            lines.append("[%s] %s" % (m["role"], c))
        transcript = "\n\n".join(lines)
        if len(transcript) > room:  # keep the start (the goal) and the most recent part
            transcript = transcript[: room // 3] + "\n\n[… middle omitted …]\n\n" + transcript[-(room * 2 // 3):]
        lang = detect_language(next((m["content"] for m in head if m["role"] == "user"), ""))
        msgs = [{"role": "system", "content": "You compress a coding-agent conversation so work can continue without it. "
                 "Be faithful and specific; never invent anything."},
                {"role": "user", "content": "Summarize this conversation in %s with these sections:\n"
                 "## 목표 (the user's requests, exact requirements)\n## 한 일 (what was done, results of commands/tests)\n"
                 "## 파일 (files created/changed and what is in them)\n## 결정·사실 (decisions, constraints, facts found, errors)\n"
                 "## 남은 일 (what is still to do, next step)\n\nConversation:\n%s" % (lang, transcript)}]
        try:
            summary, _ = self._call(msgs, lambda s: None, think=False, show_thinking=False)
            summary = split_thinking(summary)[1].strip()
        except ModelError:
            return False
        if not summary:
            return False
        self.history = [{"role": "user", "content": "[Earlier part of this conversation, summarized to save context]\n" + summary},
                        {"role": "assistant", "content": "Understood — I will continue from this summary."}] + tail
        after = self._history_tokens()
        emit("notice", level="info", text="%s이전 대화를 요약했습니다 — 컨텍스트 %s → %s 토큰 (최근 메시지 %d개는 그대로)"
             % ("" if manual else "컨텍스트가 가득 차기 전에 자동으로 ", fmt_tokens(before), fmt_tokens(after), len(tail)))
        return True

    def _fit(self, system: str) -> List[Dict[str, str]]:
        """System + as much recent history as fits; old tool results are shortened first."""
        budget = self._budget() - estimate_tokens(system)
        msgs = [dict(m) for m in self.history]
        total = sum(estimate_tokens(m["content"]) for m in msgs)
        i = 0
        while total > budget and i < len(msgs) - 2:
            m = msgs[i]
            if m["role"] == "user" and m["content"].startswith("<tool_result") and len(m["content"]) > 300:
                old = estimate_tokens(m["content"])
                m["content"] = "<tool_result>[older tool output omitted to save context]</tool_result>"
                total -= old - estimate_tokens(m["content"])
            i += 1
        while total > budget and len(msgs) > 2:
            total -= estimate_tokens(msgs.pop(0)["content"])
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        return [{"role": "system", "content": system}] + msgs

    def _call(self, messages: List[Dict[str, str]], status: Callable[[str], None],
              think: Optional[bool] = None, show_thinking: bool = True, refit: bool = False) -> Tuple[str, str]:
        progress = ui.Progress(self.cfg.verbose, show_status=False)  # stats are shown once per turn
        self._n = getattr(self, "_n", 0) + 1
        live = {"id": "th%d_%d" % (int(time.time()), self._n), "buf": "", "on": False, "done": not show_thinking,
                "t0": time.time(), "last": 0.0}
        self.last_think = None

        def tap(piece: str) -> None:
            self.check_stop()
            progress(piece)
            if live["done"]:
                return
            live["buf"] += piece
            b = live["buf"]
            if not live["on"]:
                if "<think>" in b or ("</think>" in b and "<think>" not in b):
                    live["on"] = True
                elif len(b.lstrip()) > 8:
                    live["done"] = True  # no thinking in this answer
                    return
            if "</think>" in b:  # the answer starts now: show the finished thinking (folded)
                text = b.split("</think>", 1)[0].replace("<think>", "").strip()
                live["done"] = True
                if text:
                    secs = round(time.time() - live["t0"], 1)
                    emit("thinking", id=live["id"], text=text, seconds=secs)
                    self.last_think = live["id"]
                return
            if time.time() - live["last"] > 0.4:
                live["last"] = time.time()
                emit("thinking_live", id=live["id"], text=b.replace("<think>", "").strip())

        try:
            extra = {"refit": True, "tools": TOOL_SCHEMAS if not self._readonly else
                     [t for t in TOOL_SCHEMAS if t["function"]["name"] not in ("write_file", "edit_file", "bash")]} \
                if refit else {}
            res = self.client.chat(messages, on_token=tap, think=think, **extra)
        finally:
            progress.done()
        return res.text, res.finish_reason

    # ------------------------------------------------------------------- run
    def chat(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})
        msgs = [{"role": "system", "content": CHAT_SYSTEM.format(language=detect_language(text))}] + self.history[-6:]
        raw, _ = self._call(msgs, lambda s: None, think=False, show_thinking=False)
        thinking, visible = split_thinking(raw)
        reply = visible.strip() or raw.strip()
        self.history.append({"role": "assistant", "content": reply})
        emit("assistant", text=reply)
        return reply

    def run(self, text: str, effort: str = "medium", readonly: bool = False) -> str:
        if effort == "auto":
            effort = "medium" if wants_thinking(text, "auto") else "none"
        think = None if effort in ("medium", "high") else False  # simple requests: model's thinking off
        self._readonly = readonly
        nudges = 0
        self._wrote = 0  # files created/changed in this request
        for t in self._interjections():  # typed before the first step: part of the request
            self._add_interjection(t)
        self.history.append({"role": "user", "content": text})
        final = ""
        for step in range(MAX_STEPS):
            self.check_stop()
            system = self._system(text, effort, readonly)
            self.maybe_compact(system)  # summarize old messages before the context overflows
            t0 = time.time()
            try:
                raw, finish = self._call(self._fit(system), lambda s: None, think=think, refit=True)
            except ContextRefit:  # the model process crashed: smaller prompt, then try this step again
                emit("notice", level="warn", text="모델 서버가 멈춰서 프롬프트를 줄여 다시 시도합니다 (컨텍스트 %dK)"
                     % (self.client._num_ctx() // 1024))
                system = self._system(text, effort, readonly)
                self.compact(self._budget() - estimate_tokens(system)) if len(self.history) > 4 else None
                raw, finish = self._call(self._fit(system), lambda s: None, think=think, refit=True)
            thinking, visible = split_thinking(raw)
            if thinking and not self.last_think:  # (already shown live when the answer started)
                emit("thinking", text=thinking, seconds=round(time.time() - t0, 1))
            calls, prose = parse_tool_calls(visible)
            if prose:
                emit("assistant", text=prose)
                final = prose
            self.history.append({"role": "assistant", "content": visible or raw})
            if not calls:  # about to stop: first handle anything the user added meanwhile, in order
                added = self._interjections()
                if added:
                    for t in added:
                        self._add_interjection(t)
                    continue
            unfinished = bool(_MAKE.search(text)) and self._wrote == 0  # asked to make/change files, none touched yet
            tail = (prose or "").strip()[-300:]
            if not calls and not readonly and nudges < 3 and finish != "length" and (step > 0 or _CODE_TASK.search(text)) and \
                    (_REFUSAL.search(prose or "") or _CODE_BLOCK.search(prose or "") or _HANDBACK.search(prose or "")
                     or _INTENT.search(tail) or unfinished):
                nudges += 1  # it has tools: make it do the work itself, to the end
                emit("notice", level="info", text="아직 끝나지 않아 모델이 직접 이어서 하도록 다시 요청합니다 (%d/3)" % nudges)
                self.history.append({"role": "user", "content": (
                    "Do not hand the work back to me and do not ask me to run or change anything. You have tools on "
                    "this computer: do it yourself now — create/edit files with write_file / edit_file, run and check "
                    "with bash (fix failing commands, e.g. use the grep/glob tools or PowerShell on Windows). Continue "
                    "until my original request is fully done:\n" + text[:1500])})
                continue
            if not calls:
                if finish == "length" and step < MAX_STEPS - 1:
                    self.history.append({"role": "user", "content": "Your reply was cut off. Continue exactly where you stopped."})
                    continue
                break
            results = []
            for call in calls[:8]:
                self.check_stop()
                results.append(self._execute(call, readonly))
            added = self._interjections()  # typed while working: added after these results, in order
            if added:
                results.append("\n".join("[The user added while you were working — include this, in order, after the "
                                         "current step: %s]" % t for t in added))
                for t in added:
                    emit("user", text=t, interject=True)
            self.history.append({"role": "user", "content": "\n".join(results)})
        else:
            emit("notice", level="warn", text="작업 단계가 너무 많아 멈췄습니다 (%d단계). 이어서 하려면 '계속'이라고 입력하세요." % MAX_STEPS)
        return final

    def _execute(self, call: Dict, readonly: bool) -> str:
        name, args = call["name"], call["arguments"]
        if name in ("write_file", "edit_file"):
            self._wrote = getattr(self, "_wrote", 0) + 1
        self._n = getattr(self, "_n", 0) + 1
        cid = "t%d_%d" % (int(time.time()), self._n)
        title = tool_title(name, args)
        emit("tool", id=cid, name=name, title=title, input=_brief_input(name, args))
        if readonly and name in ("write_file", "edit_file", "bash"):
            emit("tool_result", id=cid, ok=False, summary="질문 모드에서는 변경할 수 없음")
            return _result(name, False, "This is read-only question mode; do not modify files or run commands.")
        ask, danger = self.perms.needs_ask(name, args)
        if ask:
            pid = "p" + cid[1:]
            detail = str(args.get("command") or args.get("path") or "")
            req = {"id": pid, "tool": name, "title": _perm_title(name, args), "detail": detail, "danger": danger}
            if name in ("write_file", "edit_file"):
                req["diff"] = _clip(self.tools.preview(name, args), 6000)
            decision = self.ask_permission(req)
            if decision == "deny":
                emit("tool_result", id=cid, ok=False, summary="사용자가 거부함")
                return _result(name, False, "The user DENIED this action. Do not retry it; choose another approach or ask the user.")
            if decision == "always":
                self.perms.remember(name, args)
        ok, summary, output, extra = self.tools.run(name, args)
        if name == "bash":
            extra.setdefault("_show", True)  # the terminal shows the first lines of command output
        emit("tool_result", id=cid, ok=ok, summary=summary, output=_clip(output, 6000), **extra)
        body = output if output else summary
        if extra.get("diff") and not output:
            body = summary + "\n" + _clip(extra["diff"], 3000)
        return _result(name, ok, body)


def _result(name: str, ok: bool, body: str) -> str:
    return "<tool_result name=\"%s\" status=\"%s\">\n%s\n</tool_result>" % (name, "ok" if ok else "error", body)


def _brief_input(name: str, args: Dict) -> Dict:
    out = {}
    for k, v in args.items():
        s = v if isinstance(v, (int, float, bool)) else str(v)
        out[k] = s if not isinstance(s, str) or len(s) < 4000 else s[:4000] + "…"
    return out


def _perm_title(name: str, args: Dict) -> str:
    if name == "bash":
        return "명령 실행"
    if name == "write_file":
        return "파일 쓰기: %s" % args.get("path", "")
    if name == "edit_file":
        return "파일 수정: %s" % args.get("path", "")
    return "%s 실행" % name


def turn_stats(t0: float, before_in: int, before_out: int, usage=None) -> str:
    """This turn's tokens/speed/time. With a session Usage, counts only this session's calls."""
    src = usage if usage is not None else STATS
    dur = time.time() - t0
    tin = src.prompt_tokens - before_in
    tout = src.output_tokens - before_out
    speed = tout / dur if dur > 0 else 0
    last = src.last
    if last and last.speed:
        speed = last.speed
    return "%s tok · %.1f tok/s · %.1f초" % (fmt_tokens(tin + tout), speed, dur)


# ----------------------------------------------------------- optional: Aider

def aider_available() -> bool:
    return shutil.which("aider") is not None


def run_aider(cfg: Config, root: Path, text: str, stop: threading.Event) -> int:
    """Delegate a task to Aider (open-source AI pair programmer) using the same local model."""
    exe = shutil.which("aider")
    if not exe:
        emit("error", text="Aider 가 설치되어 있지 않습니다:  pip install aider-chat")
        return 1
    env = dict(os.environ)
    if cfg.provider == "ollama":
        model = "ollama_chat/" + cfg.model
        base = cfg.base_url.rstrip("/")
        env["OLLAMA_API_BASE"] = base[:-3] if base.endswith("/v1") else base
    else:
        model = "openai/" + cfg.model
        env["OPENAI_API_BASE"] = cfg.base_url
        env["OPENAI_API_KEY"] = cfg.api_key or "local"
    cmd = [exe, "--model", model, "--yes-always", "--no-pretty", "--no-stream", "--no-auto-commits",
           "--no-show-model-warnings", "--message", text]
    emit("tool", id="aider", name="bash", title="Aider(%s)" % model, input={"command": " ".join(cmd[:-1]) + " --message …"})
    proc = subprocess.Popen(cmd, cwd=str(root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    lines: List[str] = []
    assert proc.stdout
    for line in proc.stdout:
        lines.append(line)
        print(ui.dim("  " + line.rstrip()))
        if stop.is_set():
            proc.kill()
            break
    proc.wait()
    emit("tool_result", id="aider", ok=proc.returncode == 0, summary="exit %d" % proc.returncode,
         output=_clip("".join(lines), 8000))
    return proc.returncode
