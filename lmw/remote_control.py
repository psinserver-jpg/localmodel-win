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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import ui

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _user_agent() -> str:
    import platform
    from . import __version__
    # A real User-Agent: Cloudflare and similar proxies block the default "Python-urllib/x.y".
    return "lmw-cli/%s (%s %s; Python %s)" % (__version__, platform.system(), platform.release(), platform.python_version())


_DOH_HOSTS: Dict[str, str] = {}  # hostname -> IP found via DNS-over-HTTPS
_real_getaddrinfo = socket.getaddrinfo


def _getaddrinfo(host, *args, **kw):
    ip = _DOH_HOSTS.get(str(host).lower()) if isinstance(host, str) else None
    return _real_getaddrinfo(ip or host, *args, **kw)


def _doh_lookup(host: str) -> Optional[str]:
    """Resolve without the computer's DNS (a stale ISP cache can break the hub's name for hours)."""
    import ssl
    ctx = ssl.create_default_context()
    for url in ("https://1.1.1.1/dns-query?name=%s&type=A" % host,
                "https://8.8.8.8/resolve?name=%s&type=A" % host):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/dns-json", "User-Agent": _user_agent()})
            with urllib.request.urlopen(req, timeout=6, context=ctx) as r:
                d = json.loads(r.read().decode("utf-8"))
            for a in d.get("Answer") or []:
                if a.get("type") == 1 and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(a.get("data", ""))):
                    return a["data"]
        except Exception:
            continue
    return None


def _dns_fallback(url: str) -> bool:
    """True if the URL's host could be resolved another way (then retry the request)."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if not host or host in _DOH_HOSTS or re.fullmatch(r"[\d.]+", host):
        return False
    ip = _doh_lookup(host)
    if not ip:
        return False
    _DOH_HOSTS[host] = ip
    socket.getaddrinfo = _getaddrinfo  # TLS still checks the real hostname; only the lookup changes
    return True


def _req(method: str, url: str, body: Optional[dict] = None, token: str = "", timeout: float = 30):
    try:
        return _req1(method, url, body, token, timeout)
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), socket.gaierror) and _dns_fallback(url):
            return _req1(method, url, body, token, timeout)
        raise


def _req1(method: str, url: str, body: Optional[dict] = None, token: str = "", timeout: float = 30):
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
    url = auth["hub"].rstrip("/") + "/api/cli/whoami"
    for attempt in range(2):
        try:
            _, d = _req("GET", url, token=auth["token"], timeout=10)
            return d.get("user")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return None
            err: OSError = OSError("서버 응답 HTTP %s%s" % (e.code, " (Hub 서버가 꺼져 있음)" if e.code in (502, 503, 504, 521, 522, 523) else ""))
        except ValueError:
            err = OSError("Hub 가 아닌 응답 (주소 확인: lmw login → Hub 주소 변경)")
        except OSError as e:
            err = OSError(_net_reason(e))
        if attempt == 0:
            time.sleep(1.5)
    raise err


def _net_reason(e: BaseException) -> str:
    """Short Korean reason for a network error."""
    r = getattr(e, "reason", e)
    t = str(r)
    if "CERTIFICATE" in t.upper() or "SSL" in t.upper():
        return "인증서(SSL) 오류: %s" % t
    if isinstance(r, socket.timeout) or "timed out" in t:
        return "응답 시간 초과"
    if isinstance(r, socket.gaierror) or "getaddrinfo" in t or "Name or service" in t:
        return "주소(DNS)를 찾을 수 없음"
    if "refused" in t.lower() or "10061" in t:
        return "연결 거부됨"
    return t


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
        except OSError as e:
            ui.warn("Hub(%s)에 연결할 수 없어 오프라인으로 시작합니다 — %s" % (auth["hub"], e))
            ui.info(ui.dim("연결되면 자동으로 원격 제어가 켜집니다"))
            auth["offline"] = "1"
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


class Channel:
    """One hub session hosted by this lmw process (the terminal's, or one opened from the web)."""

    def __init__(self, sid: str, background: bool):
        self.sid = sid
        self.background = background
        self.inbox: "queue.Queue" = queue.Queue()
        self.events: List[Dict] = []
        self.log: List[str] = []
        self.meta: Dict[str, object] = {}
        self.prompt = ""
        self.running = False
        self.closed = False
        self.last_state = None
        self.on_interrupt: Callable[[], None] = lambda: None
        self.on_control: Callable[[str, str], None] = lambda action, value: None
        self.usage = None  # stats.Usage of the shell running this session (per-session tokens/time)


class Bridge:
    """Mirrors this lmw process to the user's Hub account (always on while logged in).

    One process can host several sessions, like Claude Code: the terminal's own session plus any
    sessions opened from the website ("새 세션"), each with its own conversation and inbox.
    Only what lmw generates (structured events) is sent — the terminal screen is not scraped.
    """

    def __init__(self, auth: Dict[str, str], name: str, cwd: str, model: str,
                 mode: str = "ask", effort: str = "auto"):
        self.relay = (auth.get("relay") or auth["hub"]).rstrip("/")
        self.token = auth["token"]
        self.email = auth.get("user") or auth.get("email", "")
        self.cwd, self.model, self.mode, self.effort = cwd, model, mode, effort
        self.device = "%s:%d" % (socket.gethostname(), os.getpid())
        self.channels: Dict[str, Channel] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._started = False
        self._pending_line = ""
        self.mirror_terminal = False
        self.tui = False  # set by start(): prompt_toolkit input box instead of the keyboard thread
        self.on_new_session: Callable[[], None] = lambda: None  # set by the shell
        self.main: Channel = self.new_session()
        self._orig_out, self._orig_err = sys.stdout, sys.stderr

    # ------------------------------------------------- main-session shortcuts
    @property
    def url(self) -> str:
        return self.relay + "/"

    @property
    def session_id(self) -> str:
        return self.main.sid

    @property
    def inbox(self) -> "queue.Queue":
        return self.main.inbox

    @property
    def running(self) -> bool:
        return self.main.running

    @running.setter
    def running(self, value: bool) -> None:
        self.main.running = value

    @property
    def on_interrupt(self):
        return self.main.on_interrupt

    @on_interrupt.setter
    def on_interrupt(self, fn) -> None:
        self.main.on_interrupt = fn

    @property
    def on_control(self):
        return self.main.on_control

    @on_control.setter
    def on_control(self, fn) -> None:
        self.main.on_control = fn

    # ---------------------------------------------------------- sessions
    def new_session(self, title: str = "", background: bool = False) -> Channel:
        """background=False: the terminal moves to a fresh session. True: one more session (from the web)."""
        _, d = _req("POST", self.relay + "/api/sessions", {
            "host": socket.gethostname(), "cwd": self.cwd, "model": self.model, "title": title,
            "mode": self.mode, "effort": self.effort, "device": self.device, "background": background}, self.token)
        ch = Channel(d["id"], background)
        old = getattr(self, "main", None)
        with self._lock:
            self.channels[ch.sid] = ch
            if not background:
                if old is not None:
                    ch.on_interrupt, ch.on_control, ch.usage = old.on_interrupt, old.on_control, old.usage
                    old.closed = True  # the hub already marked it as history
                self.main = ch
        if self._started:
            threading.Thread(target=self._input_loop, args=(ch,), daemon=True).start()
        return ch

    def channel(self, sid: Optional[str]) -> Channel:
        return self.channels.get(sid or "", self.main)

    # ------------------------------------------------------------- output
    def event(self, e: Dict) -> None:
        """events.BUS sink: route the event to its session."""
        e = dict(e)
        ch = self.channel(e.pop("_sid", None))
        with self._lock:
            if e["type"] == "thinking_live":  # streaming thoughts: latest text only, not stored as history
                ch.meta["live_think"] = {"id": e.get("id", ""), "text": str(e.get("text", ""))[-20000:]}
                return
            if e["type"] in ("thinking", "assistant", "turn_end", "tool"):
                ch.meta["live_think"] = {}  # the final thinking / the answer replaces the live view
            self._flush_log_locked(ch)
            ch.events.append(e)

    def set_meta(self, sid: Optional[str] = None, **kw) -> None:
        ch = self.channel(sid)
        with self._lock:
            ch.meta.update({k: v for k, v in kw.items() if v is not None})
            if not ch.background:
                self.mode = kw.get("mode", self.mode)
                self.effort = kw.get("effort", self.effort)

    def capture(self, s: str) -> None:  # only used when mirror_terminal=True
        if not s:
            return
        with self._lock:
            text = self._pending_line + s
            lines = text.split("\n")
            self._pending_line = lines.pop()
            for line in lines:
                if "\r" in line:
                    line = line.rsplit("\r", 1)[-1]
                self.main.log.append(_ANSI.sub("", line))

    @staticmethod
    def _flush_log_locked(ch: Channel) -> None:
        lines = [l for l in ch.log if l.strip()]
        if lines:
            ch.events.append({"type": "log", "text": "\n".join(lines), "ts": time.time()})
        ch.log = []

    def flush(self, ended: bool = False, only: Optional[Channel] = None) -> None:
        from .stats import STATS
        for ch in [only] if only else list(self.channels.values()):
            if ch.closed and not ended:
                continue
            with self._lock:
                self._flush_log_locked(ch)
                events, ch.events = ch.events, []
                meta, ch.meta = ch.meta, {}
            status = ch.usage.line() if ch.usage is not None else STATS.line()
            state = (status, ch.prompt, ch.running)
            if not events and not meta and state == ch.last_state and not ended:
                continue
            body: Dict[str, object] = dict(meta)
            body.update(events=events, status=status, prompt=ch.prompt, running=ch.running, device=self.device)
            if ended:
                body["ended"] = True
            try:
                _req("POST", "%s/api/sessions/%s/events" % (self.relay, ch.sid), body, self.token, timeout=15)
                ch.last_state = state
            except (urllib.error.URLError, OSError):
                with self._lock:  # keep and retry next tick
                    ch.events = events + ch.events
                    ch.meta = dict(meta, **ch.meta)

    def _flush_loop(self) -> None:
        while not self._stop.wait(0.4):
            self.flush()

    # -------------------------------------------------------------- input
    def _input_loop(self, ch: Channel) -> None:
        while not self._stop.is_set() and not ch.closed:
            try:
                _, d = _req("GET", "%s/api/sessions/%s/input" % (self.relay, ch.sid), token=self.token, timeout=35)
            except (urllib.error.URLError, OSError):
                self._stop.wait(3)
                continue
            for msg in d.get("input") or []:
                if isinstance(msg, str):  # older hubs
                    msg = {"kind": "prompt", "text": msg}
                if msg.get("kind") == "prompt":
                    ch.inbox.put(("web", str(msg.get("text", ""))))
                    continue
                if msg.get("kind") == "file":
                    self._save_upload(ch, msg)
                    continue
                action, value = msg.get("action"), msg.get("value", "")
                if action == "interrupt":
                    ch.on_interrupt()
                elif action in ("mode", "effort", "model"):
                    ch.on_control(action, value)
                elif action == "permission":
                    ch.inbox.put(("web", PERM + "%s:%s" % (msg.get("id", ""), value)))
                elif action == "new_session":
                    threading.Thread(target=self.on_new_session, daemon=True).start()

    def _save_upload(self, ch: Channel, msg: Dict) -> None:
        """A file sent from the website: save it as <project>/uploads/<name> (never overwrites)."""
        import base64
        from .events import emit, set_context
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(msg.get("name") or "file")).strip(" .")[:120] or "file"
        folder = Path(self.cwd) / "uploads"
        try:
            data = base64.b64decode(str(msg.get("data") or ""))
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / name
            stem, suffix, n = target.stem, target.suffix, 2
            while target.exists():
                target = folder / ("%s (%d)%s" % (stem, n, suffix))
                n += 1
            target.write_bytes(data)
            set_context(ch.sid if ch.background else "", ch.background)
            emit("file", name=target.name, path="uploads/" + target.name, size=len(data))
        except (OSError, ValueError) as e:
            set_context(ch.sid if ch.background else "", ch.background)
            emit("notice", level="error", text="파일 저장 실패 (%s): %s" % (name, e))

    def _keyboard_loop(self) -> None:
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if line == "":  # EOF
                self.main.inbox.put(("eof", ""))
                return
            self.main.inbox.put(("key", line.rstrip("\r\n")))

    def read_line(self, prompt: str = "", main: bool = False) -> str:
        """Terminal session input: keyboard or the website, whichever comes first."""
        from . import tui
        ch = self.main
        if self.tui:
            if main:  # Claude-style input box; a prompt from the website ends it
                ch.prompt = "lmw ❯"
                try:
                    source, text = tui.input_box(ui.TUI["commands"], ui.TUI["hints"], ui.TUI["shift_tab"],
                                                 external=ch.inbox)
                finally:
                    ch.prompt = ""
                if source == "eof":
                    raise EOFError
                if source == "web" and not text.startswith("\x00"):
                    with ui.remote_muted():
                        print(ui.accent("> ") + text + "   " + ui.dim("[원격]"))
                elif source == "key" and text.strip():
                    with ui.remote_muted():
                        print(ui.accent("> ") + text.replace("\n", "\n  "))
                return text
            with ui.remote_muted():  # short questions (menus): keyboard only
                return input(prompt)
        with ui.remote_muted():
            sys.stdout.write(prompt)
            sys.stdout.flush()
        # a permission question is already shown on the web as a card with buttons
        ch.prompt = "" if "[a]lways" in prompt else _ANSI.sub("", prompt).strip()
        try:
            source, text = ch.inbox.get()
        finally:
            ch.prompt = ""
        if source == "eof":
            raise EOFError
        if source == "web" and not text.startswith("\x00"):
            with ui.remote_muted():
                sys.stdout.write(text + "   " + ui.dim("[원격]") + "\n")
                sys.stdout.flush()
        return text

    @staticmethod
    def read_channel(ch: Channel, prompt: str = "") -> str:
        """Input for a web-opened session (no keyboard)."""
        ch.prompt = "" if "[a]lways" in prompt else _ANSI.sub("", prompt).strip()
        try:
            source, text = ch.inbox.get()
        finally:
            ch.prompt = ""
        return text

    # ---------------------------------------------------------- lifecycle
    def start(self, keyboard: bool = True) -> None:
        from .events import BUS
        if self.mirror_terminal:
            sys.stdout = _Tee(self._orig_out, self)
            sys.stderr = _Tee(self._orig_err, self)
        from . import tui
        self.tui = keyboard and tui.available()
        keyboard = keyboard and not self.tui
        ui.set_input_hook(self.read_line)
        BUS.subscribe(self.event)
        self._started = True
        targets = [(self._flush_loop, ())] + [(self._input_loop, (ch,)) for ch in self.channels.values() if not ch.closed]
        if keyboard:
            targets.append((self._keyboard_loop, ()))
        for target, args in targets:
            threading.Thread(target=target, args=args, daemon=True).start()

    def stop(self) -> None:
        from .events import BUS
        BUS.unsubscribe(self.event)
        self._stop.set()
        ui.set_input_hook(None)
        if self.mirror_terminal:
            sys.stdout, sys.stderr = self._orig_out, self._orig_err
        for ch in list(self.channels.values()):
            ch.running = False
            if not ch.closed:
                self.flush(ended=True, only=ch)
