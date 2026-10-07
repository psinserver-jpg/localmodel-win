"""MCP (Model Context Protocol) client: lets local models use any MCP server's tools.

Servers are started on demand as child processes and spoken to with JSON-RPC over stdin/stdout (the
"stdio" transport; standard library only). Configuration lives in ~/.lmw/mcp.json in the same shape Claude
Desktop uses:  {"mcpServers": {"time": {"command": "uvx", "args": ["mcp-server-time"], "env": {}}}}

Only YOUR user-level config is read - never a file inside a project folder (a cloned repo must not be able to
make lmw start programs). Tool lists are cached, so a server is only started when the model really calls it.
Tool names the model sees: mcp_<server>_<tool>.
"""

from __future__ import annotations

import atexit
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import __version__

PROTOCOL = "2024-11-05"
START_TIMEOUT = 150   # npx / uvx may download the server the first time
CALL_TIMEOUT = 120

PRESETS: Dict[str, Dict] = {
    "time": {"command": "uvx", "args": ["mcp-server-time"], "about": "현재 시각·시간대 변환"},
    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"], "about": "웹페이지를 가져와 마크다운으로 변환"},
    "git": {"command": "uvx", "args": ["mcp-server-git", "--repository", "{cwd}"], "about": "git 상태·diff·로그·커밋"},
    "memory": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"],
               "env": {"MEMORY_FILE_PATH": "{home}/mcp-memory.json"}, "about": "지식 그래프 기억 (엔티티·관계)"},
    "sequential-thinking": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
                            "about": "단계별 사고(생각 정리) 도구"},
    "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "{cwd}"],
                   "about": "파일 읽기/쓰기/검색 (프로젝트 폴더)"},
    "everything": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-everything"], "about": "MCP 테스트용 서버"},
}
RECOMMENDED = ["time", "fetch", "git", "memory", "sequential-thinking"]
RUNTIME_HELP = {"uvx": "uv 가 필요합니다:  pip install uv   (Windows: winget install astral-sh.uv)",
                "npx": "Node.js 가 필요합니다: https://nodejs.org"}


class McpError(Exception):
    pass


def home() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw"))


def config_file() -> Path:
    return home() / "mcp.json"


def cache_file() -> Path:
    return home() / "mcp-cache.json"


def _load(path: Path) -> Dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_config() -> Dict[str, Dict]:
    cfg = _load(config_file()).get("mcpServers")
    return {k: v for k, v in (cfg or {}).items() if isinstance(v, dict) and not v.get("disabled")}


def write_config(servers: Dict[str, Dict]) -> None:
    f = config_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    data = _load(f)
    data["mcpServers"] = servers
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "x"


def full_name(server: str, tool: str) -> str:
    return ("mcp_%s_%s" % (_slug(server), _slug(tool)))[:64]


def spec_sig(spec: Dict) -> str:
    return json.dumps([spec.get("command"), spec.get("args"), spec.get("env")], sort_keys=True)


# ------------------------------------------------------------------ server

class McpServer:
    def __init__(self, name: str, spec: Dict, cwd: str):
        self.name, self.spec, self.cwd = name, spec, cwd
        self.proc: Optional[subprocess.Popen] = None
        self.tools: List[Dict] = []
        self.stderr_tail = ""
        self._id = 0
        self._pending: Dict[int, "queue.Queue"] = {}
        self._lock = threading.Lock()
        self._wlock = threading.Lock()
        self._dead = False

    # -- process
    def _expand(self, s: str) -> str:
        return s.replace("{cwd}", self.cwd).replace("{home}", str(home())).replace("${cwd}", self.cwd)

    def _command(self) -> Tuple[List[str], Dict[str, str]]:
        cmd = str(self.spec.get("command") or "")
        if not cmd:
            raise McpError("command 가 없습니다 (URL 방식 서버는 아직 지원하지 않습니다)")
        exe = shutil.which(cmd)
        if exe is None:
            raise McpError("%s 를 찾을 수 없습니다. %s" % (cmd, RUNTIME_HELP.get(Path(cmd).stem.lower(), "설치되어 있어야 합니다")))
        argv = [exe] + [self._expand(str(a)) for a in (self.spec.get("args") or [])]
        env = dict(os.environ)
        for k, v in (self.spec.get("env") or {}).items():
            env[str(k)] = self._expand(str(v))
        return argv, env

    def start(self, timeout: float = START_TIMEOUT) -> None:
        if self.proc is not None and self.proc.poll() is None and not self._dead:
            return
        argv, env = self._command()
        self._dead = False
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                                     cwd=self.cwd, text=True, encoding="utf-8", errors="replace", bufsize=1, **kw)
        threading.Thread(target=self._read_out, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        try:
            self.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                        "clientInfo": {"name": "lmw", "version": __version__}}, timeout)
            self.notify("notifications/initialized")
            self.tools = self._list_tools(min(timeout, 60))
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        p, self.proc = self.proc, None
        self._dead = True
        if p is not None:
            try:
                p.stdin.close()
            except Exception:
                pass
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    # -- plumbing
    def _read_err(self) -> None:
        p = self.proc
        try:
            for line in p.stderr:  # type: ignore[union-attr]
                self.stderr_tail = (self.stderr_tail + line)[-4000:]
        except Exception:
            pass

    def _read_out(self) -> None:
        p = self.proc
        try:
            for line in p.stdout:  # type: ignore[union-attr]
                line = line.strip()
                if not line.startswith("{"):
                    continue  # stray log line on stdout
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if "id" in msg and ("result" in msg or "error" in msg) and "method" not in msg:
                    q = self._pending.get(msg["id"])
                    if q is not None:
                        q.put(msg)
                elif "method" in msg and "id" in msg:  # the server asks us something
                    self._answer_server_request(msg)
        except Exception:
            pass
        finally:
            self._dead = True
            for q in list(self._pending.values()):
                q.put({"error": {"message": "서버가 종료되었습니다. " + self.stderr_tail.strip()[-500:]}})

    def _send(self, obj: Dict) -> None:
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        with self._wlock:
            try:
                self.proc.stdin.write(line)  # type: ignore[union-attr]
                self.proc.stdin.flush()  # type: ignore[union-attr]
            except Exception as e:
                raise McpError("서버에 보내지 못했습니다: %s" % e)

    def _answer_server_request(self, msg: Dict) -> None:
        method = msg.get("method")
        if method == "ping":
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {}})
        elif method == "roots/list":
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {"roots": [{"uri": Path(self.cwd).resolve().as_uri(), "name": "project"}]}})
        else:
            self._send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Method not found"}})

    def notify(self, method: str, params: Optional[Dict] = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, **({"params": params} if params else {})})

    def request(self, method: str, params: Optional[Dict] = None, timeout: float = CALL_TIMEOUT,
                stop: Optional[Callable[[], None]] = None) -> Dict:
        with self._lock:
            self._id += 1
            rid = self._id
        q: "queue.Queue" = queue.Queue()
        self._pending[rid] = q
        try:
            self._send({"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})})
            end = time.time() + timeout
            while True:
                try:
                    msg = q.get(timeout=0.25)
                    break
                except queue.Empty:
                    if stop:
                        stop()  # raises when the user pressed Ctrl+C
                    if self._dead and q.empty():
                        raise McpError("서버가 종료되었습니다. " + self.stderr_tail.strip()[-500:])
                    if time.time() > end:
                        raise McpError("%s 응답 시간 초과 (%ds)" % (method, timeout))
            if "error" in msg:
                raise McpError(str(msg["error"].get("message") if isinstance(msg["error"], dict) else msg["error"]))
            return msg.get("result") or {}
        finally:
            self._pending.pop(rid, None)

    def _list_tools(self, timeout: float) -> List[Dict]:
        tools: List[Dict] = []
        cursor = None
        for _ in range(20):
            res = self.request("tools/list", {"cursor": cursor} if cursor else {}, timeout)
            tools += [t for t in res.get("tools", []) if isinstance(t, dict) and t.get("name")]
            cursor = res.get("nextCursor")
            if not cursor:
                break
        return tools

    def call_tool(self, tool: str, arguments: Dict, stop: Optional[Callable[[], None]] = None) -> Tuple[bool, str]:
        self.start()
        res = self.request("tools/call", {"name": tool, "arguments": arguments or {}}, CALL_TIMEOUT, stop)
        parts: List[str] = []
        for c in res.get("content") or []:
            kind = c.get("type")
            if kind == "text":
                parts.append(str(c.get("text", "")))
            elif kind == "image":
                parts.append("[image omitted: %s]" % c.get("mimeType", "image"))
            elif kind == "resource":
                r = c.get("resource") or {}
                parts.append(str(r.get("text") or r.get("uri") or "[resource]"))
            else:
                parts.append(json.dumps(c, ensure_ascii=False)[:500])
        if not parts and res.get("structuredContent") is not None:
            parts.append(json.dumps(res["structuredContent"], ensure_ascii=False, indent=1))
        return (not res.get("isError")), "\n".join(parts).strip()


# ----------------------------------------------------------------- manager

class Manager:
    def __init__(self, cwd: str):
        self.cwd = cwd
        self.servers: Dict[str, McpServer] = {}
        self._index: Dict[str, Tuple[str, Dict]] = {}
        self.reload()

    def reload(self) -> None:
        cfg = read_config()
        for gone in [n for n in self.servers if n not in cfg or spec_sig(cfg[n]) != spec_sig(self.servers[n].spec)]:
            self.servers.pop(gone).stop()
        for name, spec in cfg.items():
            if name not in self.servers:
                self.servers[name] = McpServer(name, spec, self.cwd)
        cache = _load(cache_file())
        self._index = {}
        for name, srv in self.servers.items():
            ent = cache.get(name) or {}
            tools = srv.tools or (ent.get("tools") if ent.get("sig") == spec_sig(srv.spec) else []) or []
            for t in tools:
                self._index[full_name(name, t["name"])] = (name, t)

    def tool_list(self) -> List[Tuple[str, str, Dict]]:
        """[(full name, server, tool dict)] for every known tool."""
        return [(fn, s, t) for fn, (s, t) in sorted(self._index.items())]

    def classify(self, full: str) -> Tuple[str, bool]:
        ent = self._index.get(full)
        hint = ((ent[1].get("annotations") or {}) if ent else {}).get("readOnlyHint")
        return ("read" if hint is True else "run"), False

    def discover(self, name: str, timeout: float = START_TIMEOUT) -> List[Dict]:
        srv = self.servers[name]
        srv.start(timeout)
        cache = _load(cache_file())
        cache[name] = {"sig": spec_sig(srv.spec), "tools": srv.tools, "time": time.strftime("%Y-%m-%d %H:%M")}
        cache_file().parent.mkdir(parents=True, exist_ok=True)
        cache_file().write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        self.reload()
        return srv.tools

    def call(self, full: str, args: Dict, stop: Optional[Callable[[], None]] = None):
        ent = self._index.get(full)
        if ent is None:
            return False, "알 수 없는 MCP 도구", "Unknown MCP tool %s. Known: %s" % (full, ", ".join(list(self._index)[:20])), {}
        server, tool = ent
        try:
            ok, text = self.servers[server].call_tool(tool["name"], args if isinstance(args, dict) else {}, stop)
        except McpError as e:
            return False, "MCP 오류", "MCP server %r: %s" % (server, e), {}
        from .agent import _clip
        return ok, ("%s: %s" % (server, tool["name"])) if ok else "MCP 도구 오류", _clip(text) or "(empty result)", {}

    def schemas(self, read_only: bool = False) -> List[Dict]:
        out = []
        for fn, server, t in self.tool_list():
            if read_only and self.classify(fn)[0] != "read":
                continue
            params = t.get("inputSchema") if isinstance(t.get("inputSchema"), dict) else {}
            params = dict(params or {})
            params.setdefault("type", "object")
            params.setdefault("properties", {})
            out.append({"type": "function", "function": {"name": fn, "description": ("[%s] %s" % (server, t.get("description") or ""))[:400],
                                                         "parameters": params}})
        return out

    def docs(self, read_only: bool = False, limit: int = 40) -> str:
        rows = []
        for fn, server, t in self.tool_list():
            if read_only and self.classify(fn)[0] != "read":
                continue
            props = list(((t.get("inputSchema") or {}).get("properties") or {}))[:5]
            rows.append("- %s(%s): %s" % (fn, ", ".join(props), " ".join(str(t.get("description") or "").split())[:110]))
        if not rows:
            return ""
        more = "\n(... and %d more)" % (len(rows) - limit) if len(rows) > limit else ""
        return "# External tools (MCP servers)\n" + "\n".join(rows[:limit]) + more

    def stop_all(self) -> None:
        for s in self.servers.values():
            s.stop()


_MANAGER: Optional[Manager] = None


def manager(cwd: Optional[str] = None) -> Manager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = Manager(cwd or os.getcwd())
        atexit.register(lambda: _MANAGER and _MANAGER.stop_all())
    return _MANAGER


def classify(full: str) -> Tuple[str, bool]:
    return manager().classify(full)


# ---------------------------------------------------------------- commands

def _runtime_ok(spec: Dict) -> Optional[str]:
    cmd = str(spec.get("command") or "")
    if shutil.which(cmd) is None:
        return "%s 없음 — %s" % (cmd, RUNTIME_HELP.get(Path(cmd).stem.lower(), "설치가 필요합니다"))
    return None


def add_server(name: str, spec: Dict, cwd: str, log: Callable[[str], None], verify: bool = True) -> bool:
    spec = {k: v for k, v in spec.items() if k != "about"}
    servers = dict(_load(config_file()).get("mcpServers") or {})
    servers[name] = spec
    write_config(servers)
    mgr = manager(cwd)
    mgr.cwd = cwd
    mgr.reload()
    problem = _runtime_ok(spec)
    if problem:
        log("%s: 등록했지만 시작할 수 없습니다 — %s" % (name, problem))
        return False
    if not verify:
        log("%s: 등록함" % name)
        return True
    log("%s: 서버를 시작해 도구를 확인하는 중… (처음엔 내려받느라 1분쯤 걸릴 수 있습니다)" % name)
    try:
        tools = mgr.discover(name)
    except (McpError, OSError) as e:
        log("%s: 실패 — %s" % (name, e))
        return False
    log("%s: 도구 %d개 — %s" % (name, len(tools), ", ".join(t["name"] for t in tools[:8]) + (" …" if len(tools) > 8 else "")))
    return True


def _fetch_json_from(source: str) -> Dict:
    if re.match(r"https?://", source):
        m = re.match(r"https://github\.com/([^/]+)/([^/]+)/(?:blob|tree)/([^/]+)/(.+)", source)
        url = "https://raw.githubusercontent.com/%s/%s/%s/%s" % m.groups() if m else source
        from . import netutil
        with netutil.urlopen(urllib.request.Request(url, headers={"User-Agent": "lmw-cli"}), timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(source).expanduser().read_text(encoding="utf-8"))


ADMIN = ("add", "remove", "rm", "list", "tools", "refresh", "import", "presets")


def run_command(words: List[str], cwd: str, log: Callable[[str], None] = print) -> Optional[int]:
    """`lmw mcp add|remove|list|tools|refresh|import ...` (also `/mcp ...`)."""
    if not words or words[0].lower() not in ADMIN:
        return None
    cmd, rest = words[0].lower(), words[1:]
    if cmd == "presets":
        for n, p in PRESETS.items():
            log("%-20s %s  (%s %s)" % (n, p["about"], p["command"], " ".join(p["args"])[:50]))
        return 0
    if cmd == "list":
        cfg = read_config()
        if not cfg:
            log("MCP 서버가 없습니다.  mcp add --defaults  (추천 5개)   |   mcp presets  (목록)   |   mcp add <이름> -- <명령> [인자…]")
            return 0
        mgr = manager(cwd)
        mgr.reload()
        for n, spec in cfg.items():
            count = sum(1 for _f, s, _t in mgr.tool_list() if s == n)
            problem = _runtime_ok(spec)
            log("%-20s 도구 %s개   %s %s%s" % (n, count if count else "?", spec.get("command"), " ".join(map(str, spec.get("args") or []))[:50],
                                              "   ⚠ " + problem if problem else ""))
        return 0
    if cmd in ("remove", "rm"):
        servers = dict(_load(config_file()).get("mcpServers") or {})
        gone = [n for n in rest if servers.pop(n, None) is not None]
        write_config(servers)
        if _MANAGER:
            _MANAGER.reload()
        log("삭제: %s" % (", ".join(gone) if gone else "없음"))
        return 0 if gone else 1
    if cmd == "tools":
        mgr = manager(cwd)
        mgr.reload()
        rows = [(f, s, t) for f, s, t in mgr.tool_list() if not rest or s in rest]
        for f, s, t in rows:
            log("%s — %s" % (f, " ".join(str(t.get("description") or "").split())[:100]))
        if not rows:
            log("알려진 도구가 없습니다. mcp refresh 로 서버를 확인하세요")
        return 0
    if cmd == "refresh":
        mgr = manager(cwd)
        mgr.reload()
        bad = 0
        for n in (rest or list(read_config())):
            try:
                log("%s: 도구 %d개" % (n, len(mgr.discover(n))))
            except (McpError, OSError, KeyError) as e:
                bad += 1
                log("%s: 실패 — %s" % (n, e))
        return 1 if bad else 0
    if cmd == "import":
        only = []
        srcs = []
        i = 0
        while i < len(rest):
            if rest[i] == "--only" and i + 1 < len(rest):
                only += [x for x in rest[i + 1].split(",") if x]
                i += 1
            else:
                srcs.append(rest[i])
            i += 1
        if not srcs:
            log("사용법: mcp import <mcp-servers.json 주소 또는 파일> [--only 이름,이름]")
            return 2
        try:
            data = _fetch_json_from(srcs[0])
        except Exception as e:
            log("읽지 못했습니다: %s" % e)
            return 1
        found = data.get("mcpServers", data)
        servers = dict(_load(config_file()).get("mcpServers") or {})
        added, skipped = [], []
        for n, spec in found.items():
            if not isinstance(spec, dict) or (only and n not in only):
                continue
            if not spec.get("command"):
                skipped.append(n)
                continue
            servers[n] = {k: v for k, v in spec.items() if k in ("command", "args", "env")}
            added.append(n)
        write_config(servers)
        if _MANAGER:
            _MANAGER.reload()
        log("가져옴 %d개: %s%s" % (len(added), ", ".join(added[:15]), " …" if len(added) > 15 else ""))
        if skipped:
            log("건너뜀(URL 방식): %s" % ", ".join(skipped))
        log("API 키가 필요한 서버는 ~/.lmw/mcp.json 의 env 를 채우세요. 도구 확인: mcp refresh <이름>")
        return 0
    # add
    if "--defaults" in rest or "--recommended" in rest:
        ok = 0
        for n in RECOMMENDED:
            ok += 1 if add_server(n, PRESETS[n], cwd, log) else 0
        log("완료: %d/%d개 사용 가능" % (ok, len(RECOMMENDED)))
        return 0 if ok else 1
    if not rest:
        log("사용법: mcp add <프리셋>  |  mcp add --defaults  |  mcp add <이름> -- <명령> [인자…]")
        return 2
    if "--" in rest:
        i = rest.index("--")
        name, command = rest[0], rest[i + 1:]
        if not command or i != 1:
            log("사용법: mcp add <이름> -- <명령> [인자…]")
            return 2
        return 0 if add_server(name, {"command": command[0], "args": command[1:]}, cwd, log) else 1
    name = rest[0]
    if name not in PRESETS:
        log("프리셋이 아닙니다: %s  (mcp presets 로 목록 확인, 또는 mcp add %s -- <명령> …)" % (name, name))
        return 2
    return 0 if add_server(name, PRESETS[name], cwd, log) else 1
