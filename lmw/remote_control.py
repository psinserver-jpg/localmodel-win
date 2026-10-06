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
        seq = 0
        while not stop.is_set():
            try:
                _, ev = _req("GET", "%s/api/sessions/%s/events?after=%d" % (hub, s["id"], seq),
                             token=auth["token"], timeout=35)
            except (urllib.error.URLError, OSError):
                stop.wait(2)
                continue
            if ev.get("base", 0) > seq:
                sys.stdout.write(ui.dim("[… 이전 출력 생략 …]\n"))
            if ev["events"]:
                sys.stdout.write("\r\033[K")
                for text in ev["events"]:
                    sys.stdout.write(text)
                if ev["session"].get("prompt"):
                    sys.stdout.write(ev["session"]["prompt"] + " ")
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
            _req("POST", "%s/api/sessions/%s/input" % (hub, s["id"]), {"text": line}, auth["token"])
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
        self._bridge.capture(s)
        return self._real.write(s)

    def flush(self):
        return self._real.flush()

    def __getattr__(self, name):
        return getattr(self._real, name)


class Bridge:
    def __init__(self, auth: Dict[str, str], name: str, cwd: str, model: str):
        self.relay = (auth.get("relay") or auth["hub"]).rstrip("/")
        self.token = auth["token"]
        self.email = auth.get("user") or auth.get("email", "")
        self.inbox: "queue.Queue[str]" = queue.Queue()
        self._out: List[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._prompt = ""
        self._pending_line = ""  # text after the last \r or \n (status line redraws)
        self.session_id = ""
        _, d = _req("POST", self.relay + "/api/sessions", {
            "name": name, "host": socket.gethostname(), "cwd": cwd, "model": model}, self.token)
        self.session_id = d["id"]
        self._orig_out, self._orig_err = sys.stdout, sys.stderr

    @property
    def url(self) -> str:
        return self.relay + "/"

    # ------------------------------------------------------------- output
    def capture(self, s: str) -> None:
        if not s:
            return
        with self._lock:
            # Carriage-return redraws (live status line) are not appended to the log;
            # the latest one is sent as the session status instead.
            text = self._pending_line + s
            lines = text.split("\n")
            self._pending_line = lines.pop()
            for line in lines:
                if "\r" in line:
                    line = line.rsplit("\r", 1)[-1]
                self._out.append(_ANSI.sub("", line) + "\n")
            if "\r" in self._pending_line:
                self._pending_line = self._pending_line.rsplit("\r", 1)[-1]

    def _flush_loop(self) -> None:
        from .stats import STATS
        last_status = None
        while not self._stop.wait(0.4):
            self._push(STATS.line(), last_status)
            last_status = STATS.line()

    def _push(self, status: str, last_status: Optional[str], ended: bool = False) -> None:
        with self._lock:
            out, self._out = self._out, []
            partial = self._pending_line
        body: Dict[str, object] = {}
        if out:
            body["output"] = ["".join(out)]
        if status != last_status:
            body["status"] = status
        prompt = _ANSI.sub("", partial).strip() if partial else ""
        if prompt != self._prompt:
            body["prompt"] = prompt
            self._prompt = prompt
        if ended:
            body["ended"] = True
        if not body:
            return
        try:
            _req("POST", "%s/api/sessions/%s/events" % (self.relay, self.session_id), body, self.token, timeout=15)
        except (urllib.error.URLError, OSError):
            with self._lock:  # keep the output and retry next tick
                self._out = out + self._out

    # -------------------------------------------------------------- input
    def _input_loop(self) -> None:
        url = "%s/api/sessions/%s/input" % (self.relay, self.session_id)
        while not self._stop.is_set():
            try:
                _, d = _req("GET", url, token=self.token, timeout=35)
                for text in d.get("input") or []:
                    self.inbox.put(("web", text))
            except (urllib.error.URLError, OSError):
                self._stop.wait(3)

    def _keyboard_loop(self) -> None:
        while not self._stop.is_set():
            line = sys.stdin.readline()
            if line == "":  # EOF
                self.inbox.put(("eof", ""))
                return
            self.inbox.put(("key", line.rstrip("\r\n")))

    def read_line(self, prompt: str = "") -> str:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        source, text = self.inbox.get()
        if source == "eof":
            raise EOFError
        if source == "web":
            sys.stdout.write(text + "   " + ui.bold("[원격]") + "\n")  # echo so both sides see it
            sys.stdout.flush()
        else:
            self.capture(text + "\n")  # keyboard echo is done by the terminal; mirror it to the web
        return text

    # ---------------------------------------------------------- lifecycle
    def start(self, keyboard: bool = True) -> None:
        sys.stdout = _Tee(self._orig_out, self)
        sys.stderr = _Tee(self._orig_err, self)
        ui.set_input_hook(self.read_line)
        targets = [self._flush_loop, self._input_loop] + ([self._keyboard_loop] if keyboard else [])
        for target in targets:
            threading.Thread(target=target, daemon=True).start()

    def stop(self) -> None:
        from .stats import STATS
        self._stop.set()
        ui.set_input_hook(None)
        sys.stdout, sys.stderr = self._orig_out, self._orig_err
        self._push(STATS.line(), None, ended=True)
