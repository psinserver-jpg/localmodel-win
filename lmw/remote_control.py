"""Account login and the always-on hub connection.

- `lmw` refuses to work until the computer is logged in to an LMW Hub account.
- Login: the CLI shows a link -> the hub site opens -> log in (Google or ID/password)
  -> press "로그인 승인하기" -> this CLI receives a token. (Or type ID/password here.)
- While the shell runs, it is always published to the hub (outbound HTTPS/HTTP only):
  the owner sees it on the site and prompts typed there arrive here.
"""

from __future__ import annotations

import json
import os
import queue
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from . import ui

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _user_agent() -> str:
    import platform
    from . import __version__
    # A real User-Agent: Cloudflare and similar proxies block the default "Python-urllib/x.y".
    return "lmw-cli/%s (%s %s; Python %s)" % (__version__, platform.system(), platform.release(), platform.python_version())


def _req(method: str, url: str, body: Optional[dict] = None, token: str = "", timeout: float = 30):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": _user_agent()}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8") or "{}")


DEFAULT_HUB = os.environ.get("LMW_HUB", "https://psin.ai.kr")


def auth_file() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "auth.json"


def load_auth() -> Optional[Dict[str, str]]:
    try:
        d = json.loads(auth_file().read_text(encoding="utf-8"))
        return d if d.get("token") and d.get("hub") else None
    except (OSError, ValueError):
        return None


def save_auth(data: Dict[str, str]) -> None:
    f = auth_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass


def whoami(auth: Dict[str, str]) -> Optional[str]:
    """User name if the saved token is valid; None if rejected. Raises OSError if the hub is unreachable."""
    try:
        _, d = _req("GET", auth["hub"].rstrip("/") + "/api/cli/whoami", token=auth["token"], timeout=8)
        return d.get("user")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return None
        raise OSError("hub error %s" % e.code)


def _device_name() -> str:
    import platform
    return "%s (%s %s)" % (socket.gethostname(), platform.system(), platform.release())


def login(hub: str = "", open_browser: bool = True) -> Optional[Dict[str, str]]:
    """Interactive login screen. Returns the saved auth dict, or None."""
    hub = (hub or DEFAULT_HUB).rstrip("/")
    if not hub.startswith(("http://", "https://")):
        hub = "http://" + hub
    ui.box("LMW 로그인", ["lmw 를 사용하려면 Google 계정으로 로그인해야 합니다.", "Hub: " + hub])
    choice = ui.menu("로그인", [("Google 계정으로 로그인", "링크가 열리면 Google 로그인 → [로그인 승인하기]"),
                              ("Hub 주소 변경", hub)], 0)
    if choice == 1:
        new = ui.read_line("  Hub 주소 > ").strip()
        return login(new or hub, open_browser) if new else None
    if choice != 0:
        return None
    try:
        _, start = _req("POST", hub + "/api/device/start", {"device": _device_name()})
    except urllib.error.HTTPError as e:
        _explain_http(hub, e)
        return None
    except (urllib.error.URLError, OSError) as e:
        ui.err("Hub 에 연결할 수 없습니다: %s (%s)" % (hub, e))
        ui.info("인터넷 연결과 Hub 주소를 확인하세요")
        return None
    url = "%s/device?code=%s" % (hub, start["code"])
    print()
    ui.box("아래 링크를 열고 Google 로그인 → [로그인 승인하기]", [url], "35")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    ui.info("승인을 기다리는 중… (Ctrl+C 취소)")
    deadline = time.time() + start.get("expires_in", 600)
    try:
        while time.time() < deadline:
            try:
                status, d = _req("GET", "%s/api/device/poll?code=%s" % (hub, start["code"]), timeout=10)
            except urllib.error.HTTPError as e:
                ui.err("로그인 요청이 %s 되었습니다" % ("거부" if e.code == 403 else "만료"))
                return None
            except (urllib.error.URLError, OSError):
                status, d = 0, {}
            if status == 200 and d.get("token"):
                auth = {"hub": hub, "token": d["token"], "user": d["user"]}
                save_auth(auth)
                ui.ok("로그인 완료: %s" % d["user"])
                return auth
            time.sleep(2)
    except KeyboardInterrupt:
        print()
        return None
    ui.err("시간이 초과되었습니다. 다시 실행하세요")
    return None


def _explain_http(hub: str, e: urllib.error.HTTPError) -> None:
    try:
        body = e.read().decode("utf-8", errors="replace")[:2000]
    except Exception:
        body = ""
    server = (e.headers.get("Server") or "") if e.headers else ""
    ui.err("Hub 가 요청을 거부했습니다: %s (HTTP %s)" % (hub, e.code))
    if "cloudflare" in server.lower() or "cloudflare" in body.lower():
        ui.info("Cloudflare 가 차단했습니다 (봇 차단). 관리자: Cloudflare → 보안 → Bots 에서 Bot Fight Mode 끄기,")
        ui.info("또는 DNS 에서 이 도메인의 주황색 구름을 회색(DNS only)으로 바꾸세요")
    elif body.strip().startswith("{"):
        try:
            ui.info(json.loads(body).get("error", ""))
        except ValueError:
            pass


def _password_login(hub: str) -> Optional[Dict[str, str]]:
    import getpass
    user = ui.read_line("  ID > ").strip()
    pw = getpass.getpass("  비밀번호 > ")
    try:
        _, d = _req("POST", hub + "/api/login", {"id": user, "password": pw, "client": "cli", "device": _device_name()})
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read() or b"{}").get("error", "")
        except ValueError:
            msg = ""
        ui.err("로그인 실패: %s" % (msg or e.code))
        return None
    except (urllib.error.URLError, OSError) as e:
        ui.err("Hub 에 연결할 수 없습니다: %s (%s)" % (hub, e))
        return None
    auth = {"hub": hub, "token": d["token"], "user": d["user"]}
    save_auth(auth)
    ui.ok("로그인 완료: %s" % d["user"])
    return auth


def list_sessions(auth: Dict[str, str]) -> List[Dict]:
    _, d = _req("GET", auth["hub"].rstrip("/") + "/api/sessions", token=auth["token"], timeout=10)
    return d.get("sessions", [])


def watch(auth: Dict[str, str], exclude: str = "") -> int:
    """Show another computer's live lmw screen here; lines typed here are sent to it."""
    hub = auth["hub"].rstrip("/")
    try:
        sessions = [s for s in list_sessions(auth) if s["alive"] and s["id"] != exclude]
    except (urllib.error.URLError, OSError) as e:
        ui.err("Hub 에 연결할 수 없습니다: %s" % e)
        return 1
    if not sessions:
        ui.warn("지금 실행 중인 다른 컴퓨터의 lmw 가 없습니다")
        return 1
    i = 0
    if len(sessions) > 1:
        i = ui.menu("어느 컴퓨터를 볼까요?", [("💻 " + s["host"], "📁 " + s["cwd"]) for s in sessions], 0)
        if i < 0:
            return 1
    s = sessions[i]
    ui.box("💻 %s 실시간 화면" % s["host"], ["📁 " + s["cwd"], "입력하면 그 컴퓨터로 전달됩니다 · 나가기: /detach (또는 Ctrl+C)"], "35")
    stop = threading.Event()

    def pump():
        from .events import render
        seq = 0
        while not stop.is_set():
            try:
                _, ev = _req("GET", "%s/api/sessions/%s/events?after=%d" % (hub, s["id"], seq),
                             token=auth["token"], timeout=35)
            except (urllib.error.URLError, OSError):
                stop.wait(2)
                continue
            for e in ev["events"]:
                if e.get("type") == "log":
                    sys.stdout.write(ui.dim(str(e.get("text", ""))) + "\n")
                elif e.get("type") == "user":
                    sys.stdout.write(ui.bold("> ") + str(e.get("text", "")) + "\n")
                else:
                    render(e)
            sys.stdout.flush()
            seq = ev["next"]
            if not ev["session"]["alive"]:
                ui.info("그 컴퓨터의 lmw 가 종료되었습니다 (Enter 로 돌아가기)")
                stop.set()

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        while not stop.is_set():
            line = ui.read_line("")  # shares stdin with the bridge's keyboard reader
            if stop.is_set() or line.strip() == "/detach":
                break
            _req("POST", "%s/api/sessions/%s/input" % (hub, s["id"]), {"kind": "prompt", "text": line}, auth["token"])
    except (EOFError, KeyboardInterrupt):
        pass
    stop.set()
    print()
    ui.ok("보기 종료")
    return 0


def logout() -> None:
    auth = load_auth()
    if auth:
        try:
            _req("POST", auth["hub"].rstrip("/") + "/api/cli/logout", {}, auth["token"], timeout=5)
        except Exception:
            pass
    try:
        auth_file().unlink()
    except OSError:
        pass
    ui.ok("로그아웃 완료")


def require_login(hub: str = "") -> Optional[Dict[str, str]]:
    """Gate for every command: valid saved login, or show the login screen."""
    auth = load_auth()
    if auth:
        try:
            user = whoami(auth)
        except OSError:
            ui.warn("Hub(%s)에 연결할 수 없어 오프라인으로 시작합니다 — 원격 제어는 연결되면 다시 시도하세요" % auth["hub"])
            return auth
        if user:
            auth["user"] = user
            return auth
        ui.warn("로그인이 만료되었습니다. 다시 로그인하세요")
    return login(hub or (auth or {}).get("hub", ""))


# ------------------------------------------------------------------ bridge
class _Tee:
    """Wraps stdout: writes to the terminal and copies text to the bridge."""

    def __init__(self, real, bridge: "Bridge"):
        self._real = real
        self._bridge = bridge

    def write(self, s):
        if not ui.is_remote_muted():
            self._bridge.capture(s)
        return self._real.write(s)

    def flush(self):
        return self._real.flush()

    def __getattr__(self, name):
        return getattr(self._real, name)


PERM = "\x00perm:"  # inbox sentinels understood by the shell
CTL = "\x00ctl:"


class Bridge:
    """Mirrors this lmw session to the user's Hub account (always on while logged in).

    - structured events (from events.BUS) + raw terminal output (as "log" events) go up
    - prompts, permission answers and controls typed on the website come down
    """

    def __init__(self, auth: Dict[str, str], name: str, cwd: str, model: str,
                 mode: str = "ask", effort: str = "auto"):
        self.relay = (auth.get("relay") or auth["hub"]).rstrip("/")
        self.token = auth["token"]
        self.email = auth.get("user") or auth.get("email", "")
        self.inbox: "queue.Queue" = queue.Queue()
        self.cwd, self.model, self.mode, self.effort = cwd, model, mode, effort
        self.device = "%s:%d" % (socket.gethostname(), os.getpid())
        self._events: List[Dict] = []
        self._log: List[str] = []
        self._meta: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._prompt = ""
        self._pending_line = ""
        self.running = False
        self.on_interrupt = lambda: None
        self.on_control = lambda action, value: None
        self.session_id = ""
        self.new_session()
        self._orig_out, self._orig_err = sys.stdout, sys.stderr

    @property
    def url(self) -> str:
        return self.relay + "/"

    def new_session(self, title: str = "") -> str:
        self.flush()
        _, d = _req("POST", self.relay + "/api/sessions", {
            "host": socket.gethostname(), "cwd": self.cwd, "model": self.model, "title": title,
            "mode": self.mode, "effort": self.effort, "device": self.device}, self.token)
        with self._lock:
            self.session_id = d["id"]
            self._events, self._log = [], []
        return self.session_id

    # ------------------------------------------------------------- output
    def event(self, e: Dict) -> None:
        """events.BUS sink."""
        with self._lock:
            self._flush_log_locked()
            self._events.append(dict(e))

    def set_meta(self, **kw) -> None:
        with self._lock:
            self._meta.update({k: v for k, v in kw.items() if v is not None})
            if "mode" in kw:
                self.mode = kw["mode"]
            if "effort" in kw:
                self.effort = kw["effort"]

    def capture(self, s: str) -> None:
        if not s:
            return
        with self._lock:
            text = self._pending_line + s
            lines = text.split("\n")
            self._pending_line = lines.pop()
            for line in lines:
                if "\r" in line:
                    line = line.rsplit("\r", 1)[-1]
                self._log.append(_ANSI.sub("", line))
            if "\r" in self._pending_line:
                self._pending_line = self._pending_line.rsplit("\r", 1)[-1]

    def _flush_log_locked(self) -> None:
        lines = [l for l in self._log if l.strip()]
        if lines:
            self._events.append({"type": "log", "text": "\n".join(lines), "ts": time.time()})
        self._log = []

    def flush(self, ended: bool = False) -> None:
        from .stats import STATS
        if not self.session_id:
            return
        with self._lock:
            self._flush_log_locked()
            events, self._events = self._events, []
            meta, self._meta = self._meta, {}
            sid = self.session_id
        body: Dict[str, object] = dict(meta)
        body.update(events=events, status=STATS.line(), prompt=self._prompt, running=self.running, device=self.device)
        if ended:
            body["ended"] = True
        try:
            _req("POST", "%s/api/sessions/%s/events" % (self.relay, sid), body, self.token, timeout=15)
        except (urllib.error.URLError, OSError):
            with self._lock:  # keep and retry next tick
                if sid == self.session_id:
                    self._events = events + self._events
                    self._meta = dict(meta, **self._meta)

    def _flush_loop(self) -> None:
        last = None
        while not self._stop.wait(0.4):
            from .stats import STATS
            state = (STATS.line(), self._prompt, self.running)
            with self._lock:
                pending = bool(self._events or self._log or self._meta)
            if pending or state != last:
                self.flush()
                last = state

    # -------------------------------------------------------------- input
    def _input_loop(self) -> None:
        while not self._stop.is_set():
            sid = self.session_id
            try:
                _, d = _req("GET", "%s/api/sessions/%s/input" % (self.relay, sid), token=self.token, timeout=35)
            except (urllib.error.URLError, OSError):
                self._stop.wait(3)
                continue
            for msg in d.get("input") or []:
                if isinstance(msg, str):  # older hubs
                    msg = {"kind": "prompt", "text": msg}
                if msg.get("kind") == "prompt":
                    self.inbox.put(("web", str(msg.get("text", ""))))
                    continue
                action, value = msg.get("action"), msg.get("value", "")
                if action == "interrupt":
                    self.on_interrupt()
                elif action in ("mode", "effort"):
                    self.on_control(action, value)
                elif action == "permission":
                    self.inbox.put(("web", PERM + "%s:%s" % (msg.get("id", ""), value)))
                elif action == "new_session":
                    self.inbox.put(("web", CTL + "new_session"))

    def _keyboard_loop(self) -> None:
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if line == "":  # EOF
                self.inbox.put(("eof", ""))
                return
            self.inbox.put(("key", line.rstrip("\r\n")))

    def read_line(self, prompt: str = "") -> str:
        with ui.remote_muted():
            sys.stdout.write(prompt)
            sys.stdout.flush()
        self._prompt = _ANSI.sub("", prompt).strip()
        try:
            source, text = self.inbox.get()
        finally:
            self._prompt = ""
        if source == "eof":
            raise EOFError
        if source == "web" and not text.startswith("\x00"):
            with ui.remote_muted():
                sys.stdout.write(text + "   " + ui.dim("[원격]") + "\n")
                sys.stdout.flush()
        return text

    # ---------------------------------------------------------- lifecycle
    def start(self, keyboard: bool = True) -> None:
        from .events import BUS
        sys.stdout = _Tee(self._orig_out, self)
        sys.stderr = _Tee(self._orig_err, self)
        ui.set_input_hook(self.read_line)
        BUS.subscribe(self.event)
        targets = [self._flush_loop, self._input_loop] + ([self._keyboard_loop] if keyboard else [])
        for target in targets:
            threading.Thread(target=target, daemon=True).start()

    def stop(self) -> None:
        from .events import BUS
        BUS.unsubscribe(self.event)
        self._stop.set()
        ui.set_input_hook(None)
        sys.stdout, sys.stderr = self._orig_out, self._orig_err
        self.running = False
        self.flush(ended=True)
