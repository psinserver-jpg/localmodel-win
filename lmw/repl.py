"""Interactive LMW agent shell — `lmw` with no arguments.

Like Claude Code, but built for local models:
- A task message runs the full 8-phase workflow in the current folder.
- A question (or /ask) gets a direct answer; the model may read project files first.
- Every file change is shown and needs approval (toggle with /auto).
- /undo restores the files changed by the last task.
"""

from __future__ import annotations

import difflib
import threading
import time
import re
import shutil
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__, ui
from .checks import format_findings, run_checks
from .client import ChatClient, ModelError, strip_reasoning
from .config import Config
from .parse import FileBlock, apply_edits
from .pipeline import Pipeline
from .skills import all_skills, select_skills
from .textutil import estimate_tokens, language_rule, tail_tokens, truncate_to_tokens
from .workspace import Workspace

try:  # arrow keys + history on macOS/Linux; Windows consoles already have line editing
    import readline  # noqa: F401
except ImportError:
    pass

# (command, description, group) — drives /help, the "/" menu and Tab completion
COMMANDS = [
    ("/run", "에이전트로 작업 (파일 읽기·쓰기·명령)", "작업"),
    ("/plan", "계획 단계로 진행: 분석 → 계획 → 구현 → 검토·수정 반복 (/계획, /plan 요청)", "작업"),
    ("/ask", "질문하기 (읽기만, 변경 없음)", "작업"),
    ("/new", "새 세션 시작", "작업"),
    ("/sessions", "지난 세션 목록에서 골라 이어서 하기", "작업"),
    ("/compact", "지금까지 대화를 요약해 컨텍스트 비우기 (가득 차면 자동으로 함)", "작업"),
    ("/continue", "가장 최근 세션 이어서 하기", "작업"),
    ("/mode", "권한 모드: 매번 묻기 / 편집 자동 수락 / 전체 허용", "설정"),
    ("/effort", "생각 수준: 자동 / 빠르게 / 보통 / 깊게", "설정"),
    ("/engine", "에이전트 엔진: lmw / aider", "설정"),
    ("/resume", "중단된 작업 이어하기", "작업"),
    ("/undo", "마지막 작업 되돌리기", "작업"),
    ("/files", "프로젝트 파일 보기", "작업"),
    ("/check", "자동 검사 실행", "작업"),
    ("/diff", "git 변경 요약", "작업"),
    ("/model", "모델 선택", "모델"),
    ("/server", "모델 서버 변경 (LM Studio, vLLM, 다른 PC…)", "모델"),
    ("/setup", "처음 설정 다시 하기", "모델"),
    ("/ctx", "컨텍스트 크기 (/ctx 32768)", "모델"),
    ("/memory", "계정에 저장된 긴 기억 (on / off / clear / 상태)", "모델"),
    ("/skills", "스킬 목록", "모델"),
    ("/skill", "스킬 항상 포함 토글 (/skill web-design)", "모델"),
    ("/auto", "파일 변경 자동 승인 켜기/끄기", "설정"),
    ("/rounds", "최대 검토/수정 횟수 (/rounds 5)", "설정"),
    ("/verbose", "모델 출력 실시간 보기", "설정"),
    ("/stats", "시간 · 토큰 · 속도 통계", "설정"),
    ("/statusline", "상태줄 항목 변경", "설정"),
    ("/config", "현재 설정 보기", "설정"),
    ("/tools", "쓸 수 있는 도구·스킬·에이전트·MCP 전체 보기", "도구"),
    ("/mcp", "MCP 서버 연결 (add 이름 | list | tools | remove)", "도구"),
    ("/agents", "하위 에이전트 (list | add <GitHub 주소> | remove)", "도구"),
    ("/cmds", "가져온 슬래시 명령 (list | add <주소> | remove)", "도구"),
    ("/cmd", "가져온 슬래시 명령 실행 (/cmd 이름 인자)", "도구"),
    ("/add", "GitHub 저장소에서 스킬·에이전트·명령을 한 번에 설치", "도구"),
    ("/find", "awesome-claude-code 목록에서 도구 찾기 (/find security)", "도구"),
    ("/watch", "다른 컴퓨터의 lmw 화면 보기·조작", "계정"),
    ("/web", "이 화면을 웹에서 보는 주소", "계정"),
    ("/update", "lmw 최신 버전으로 업데이트 (자동 재시작)", "계정"),
    ("/logout", "로그아웃", "계정"),
    ("/help", "도움말", "기타"),
    ("/exit", "종료", "기타"),
]

HOME = [
    ("새 작업 요청", "무엇이든 만들거나 고치기", "task"),
    ("질문하기", "코드/파일에 대해 묻기", "ask"),
    ("이어하기", "중단된 작업 계속", "/resume"),
    ("되돌리기", "마지막 작업 취소", "/undo"),
    ("다른 컴퓨터 보기", "내 계정의 다른 PC lmw 화면", "/watch"),
    ("모델 변경", "", "/model"),
    ("전체 명령 보기", "", "/"),
    ("종료", "", "/exit"),
]


CTL_PREFIX = "\x00ctl:"
PERM_PREFIX = "\x00perm:"
MODE_LABELS = {"ask": "매번 묻기", "auto-edit": "편집 자동 수락", "full": "전체 허용"}
MODE_HINTS = {"ask": "파일 수정·명령 실행 전에 물어봄", "auto-edit": "파일 수정은 바로, 명령은 물어봄",
              "full": "모두 바로 실행 (위험한 명령만 물어봄)"}
EFFORT_LABELS = {"auto": "자동", "low": "빠르게", "medium": "보통", "high": "깊게"}
EFFORT_HINTS = {"auto": "요청 크기에 맞춰 자동 선택", "low": "최소한으로 생각", "medium": "필요할 때만 생각",
                "high": "큰 작업은 8단계(생각·계획·검토)로"}


def _ensure_prompt_toolkit() -> None:
    """The Claude-Code-style input box needs prompt_toolkit; install it once if it is missing."""
    from . import tui
    if tui.HAVE_PT or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return
    marker = Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / ".prompt_toolkit-tried"
    if marker.exists():
        return
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("1", encoding="utf-8")
    except OSError:
        pass
    ui.info(ui.dim("입력 화면 구성요소(prompt_toolkit) 설치 중… (처음 한 번)"))
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "--disable-pip-version-check",
                        "prompt_toolkit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        import importlib
        import site
        site.addsitedir(site.getusersitepackages())
        importlib.invalidate_caches()
        importlib.reload(tui)
    except Exception:
        pass
    if not tui.HAVE_PT:
        ui.warn("prompt_toolkit 설치 실패 — 기본 입력으로 실행합니다 (직접 설치: %s -m pip install prompt_toolkit)"
                % Path(sys.executable).name)


def _setup_completion() -> None:
    try:
        import readline
    except ImportError:
        return
    names = [c[0] for c in COMMANDS]

    def complete(text, state):
        opts = [n for n in names if n.startswith(text)] if text.startswith("/") else []
        return opts[state] + " " if state < len(opts) else None

    readline.set_completer(complete)
    readline.set_completer_delims(" \t\n")
    readline.parse_and_bind("tab: complete")


QUESTION_START = re.compile(
    r"^(what|why|how|where|which|who|when|is|are|can|does|do|explain|"
    r"뭐|왜|어떻게|어디|무엇|어느|언제|설명|알려)", re.IGNORECASE)

ASK_SYSTEM = """You are LMW, a senior engineer assistant running locally, working in the user's project folder.
Answer the user's question accurately and concisely. If you need to see a file first, reply with ONLY lines like:
=== READ: relative/path ===
and nothing else; the file contents will be sent to you. You may request up to 5 files at once.
Never invent file contents, APIs or facts. If you are not sure, say so.
Do not write or change files in this mode; if the user wants changes, tell them to send it as a task.
%s

Project files:
%s
"""

_READ = re.compile(r"^\s*={2,}\s*READ\s*:\s*(.+?)\s*={2,}\s*$", re.MULTILINE)


class Shell:
    def __init__(self, cfg: Config, workspace: Path, auth: Optional[Dict[str, str]] = None):
        self.cfg = cfg
        self.auth = auth
        self.root = workspace.resolve()
        from . import projects
        self.base_mode = projects.is_unchosen(self.root)  # started outside any project: jobs get their own folder
        if self.base_mode:
            self.root = projects.ensure_base().resolve()
        self.base_dir = self.root
        self.auto = False
        self.chat: List[Dict[str, str]] = []  # question-mode history
        self.done_tasks: List[str] = []  # earlier task requests this session
        self.last_run: Optional[Pipeline] = None
        self.client = ChatClient(cfg)
        from .agent import Permissions
        self.perms = Permissions(getattr(cfg, "permission_mode", "ask"))
        self.effort = getattr(cfg, "effort", "auto")
        self.engine = "lmw"  # or "aider"
        self.stop_event = threading.Event()
        self.pending: List[str] = []  # prompts that arrived while busy (e.g. typed on the web)
        self.agent = None
        self.titled = False
        self.sid: Optional[str] = None  # None = the terminal's session; set for sessions opened from the web
        self.background = False
        self.read = ui.read_line
        self.workers: List["Shell"] = []
        self.plan_next = False  # /plan without a request: the next request runs in plan mode
        from .stats import Usage
        self.usage = Usage()  # this session's own tokens and working time

    # ------------------------------------------------------------------ main
    bridge = None

    def loop(self) -> int:
        _setup_completion()
        _ensure_prompt_toolkit()
        from . import updater
        updater.check_in_background(self._publish_update)
        from . import hubcontent
        hubcontent.sync_in_background(wait_first=8)  # skills/agents come from psin.ai.kr
        self._setup_tui()
        self._banner()
        threading.Thread(target=self._preload, daemon=True).start()  # the first answer doesn't wait for loading
        self.connect_hub()
        from . import tui
        if not tui.available():
            print(ui.dim("  Enter = 메뉴 · / = 전체 명령 · Tab = 명령 자동완성 · 질문은 ? 로 끝내기"))
        from . import sessions
        prev = sessions.listing(str(self.root), 1)
        if prev:
            ui.info(ui.dim("지난 세션: '%s' (%s) — /continue 로 이어서 하기 · /sessions 로 고르기"
                           % ((prev[0].get("title") or "새 세션")[:40], sessions.ago(prev[0].get("updated", 0)))))
        try:
            return self._loop()
        finally:
            self.disconnect_hub()

    _hub_retry = 0.0

    def connect_hub(self, quiet: bool = False) -> None:
        """Always-on remote control: publish this session to the user's Hub account."""
        from .remote_control import Bridge, whoami
        if not self.auth or self.bridge:
            return
        self._hub_retry = time.time()
        if self.auth.get("offline"):
            if quiet:  # check in the background so the prompt never waits on the network
                auth = self.auth

                def probe():
                    try:
                        user = whoami(auth)
                    except OSError:
                        return
                    if user:
                        auth["user"] = user
                        auth.pop("offline", None)
                        self._hub_retry = 0.0  # connect before the next prompt
                threading.Thread(target=probe, daemon=True).start()
            return
        try:
            self.bridge = Bridge(self.auth, "lmw", str(self.root), self.cfg.model,
                                 mode=self.perms.mode, effort=self.effort)
            self.bridge.on_interrupt = self.stop_event.set
            self.bridge.on_control = self._remote_control
            self.bridge.on_new_session = self.open_web_session
            self.bridge.main.usage = self.usage
            self._publish_models()
            self.bridge.set_meta(sid=self.sid, commands=[[c, d] for c, d, _ in COMMANDS])
            from . import __version__, updater
            self.bridge.set_meta(sid=self.sid, version=__version__, latest=updater.latest or "")
        except Exception as e:
            self.bridge = None
            if not quiet:
                ui.warn("Hub 연결 실패 (%s) — 이 컴퓨터에서 작업하며, 연결되면 자동으로 다시 붙습니다" % e)
            return
        self.bridge.start()
        ui.info(ui.dim("● 원격 연결됨 — %s 에서 이 세션 보기·입력" % self.auth["hub"].replace("https://", "")))

    def disconnect_hub(self) -> None:
        if self.bridge:
            self.bridge.stop()
            self.bridge = None

    def home_menu(self) -> Optional[str]:
        i = ui.menu("무엇을 할까요?", [(l, h) for l, h, _ in HOME], 0)
        if i < 0:
            return None
        action = HOME[i][2]
        if action == "task":
            return self._compose("무엇을 만들거나 고칠까요?")
        if action == "ask":
            q = self._compose("무엇이 궁금한가요?")
            return "/ask " + q if q else None
        return action

    def command_menu(self) -> Optional[str]:
        i = ui.menu("명령", [(c, d) for c, d, _ in COMMANDS], 0)
        if i < 0:
            return None
        cmd = COMMANDS[i][0]
        if cmd in ("/run", "/ask"):
            text = self._compose("내용을 입력하세요")
            return cmd + " " + text if text else None
        return cmd

    @staticmethod
    def _compose(title: str) -> str:
        print(ui.bold("  " + title) + ui.dim("  (여러 줄: 줄 끝에 \\ · 빈 줄 = 취소)"))
        try:
            line = ui.read_line(ui.cyan("  ✎ "))
            while line.endswith("\\"):
                line = line[:-1] + "\n" + ui.read_line(ui.cyan("  … "))
        except EOFError:
            return ""
        return line.strip()

    def _loop(self) -> int:
        while True:
            try:
                if self.pending:
                    line = self.pending.pop(0).strip()
                    print(ui.prompt_label("lmw") + " " + line + ui.dim("   [대기열]"))
                else:
                    if self.auth and not self.bridge and time.time() - self._hub_retry > 30:
                        self.connect_hub(quiet=True)  # Hub came back: turn remote control on
                    print()
                    from . import tui
                    if not tui.available():
                        from . import updater
                        if updater.latest and not getattr(self, "_told_update", False):
                            self._told_update = True
                            ui.info(ui.yellow("새 버전 v%s 이 있습니다 — /update 로 업데이트" % updater.latest))
                        ui.status()
                    line = ui.read_line(ui.prompt_label("lmw") + " ", main=True).strip()
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print()
                continue
            if line.startswith(CTL_PREFIX):
                if line[len(CTL_PREFIX):] == "new_session":
                    self.new_session()
                elif line[len(CTL_PREFIX):] == "update":  # "업데이트" pressed on the website
                    from .events import emit
                    emit("notice", level="info", text="웹에서 업데이트를 요청했습니다 — 최신 버전을 설치하고 다시 시작합니다")
                    self._command("/update")
                elif line[len(CTL_PREFIX):] == "close_session":  # closed on the website: start a fresh one
                    ui.info(ui.dim("웹에서 이 세션을 닫았습니다 — 새 세션으로 시작합니다 (/continue 로 다시 이어서 할 수 있음)"))
                    self.new_session()
                continue
            if line.startswith(PERM_PREFIX):
                continue  # a late permission click; nothing is waiting for it
            if not line:
                from . import tui
                if tui.available():
                    continue  # like Claude Code: an empty Enter does nothing
                line = self.home_menu() or ""
            elif line == "/":
                line = self.command_menu() or ""
            if not line:
                continue
            # a trailing backslash continues the message on the next line
            while line.endswith("\\"):
                try:
                    line = line[:-1] + "\n" + ui.read_line("... ")
                except EOFError:
                    break
            try:
                if line.startswith("/"):
                    if self.run_command(line) == "exit":
                        return 0
                else:
                    self.handle(line)
            except KeyboardInterrupt:
                ui.warn("중단됨 — /resume 으로 이어서 할 수 있습니다")
            except ModelError as e:
                ui.err(str(e))
                ui.info("진행 상황은 저장됨 — /resume")
            except (FileNotFoundError, ValueError) as e:
                ui.err(str(e))

    def _setup_tui(self) -> None:
        """Claude-Code-style input box: slash completion, hint line, Shift+Tab permission modes."""
        ui.TUI["commands"] = [(c, d) for c, d, _ in COMMANDS]

        def hints():
            mode = self.perms.mode
            if mode == "ask":
                out = [("class:hint", "  ? /help · / 명령 · shift+tab 권한 모드 · Alt+Enter 줄바꿈")]
            else:
                out = [("class:mode", "  ⏵⏵ " + MODE_LABELS.get(mode, mode)),
                       ("class:hint", " (shift+tab 전환)")]
            if self.effort != "auto":
                out.append(("class:hint", " · 생각: " + EFFORT_LABELS.get(self.effort, self.effort)))
            if self.plan_next:
                out.insert(0, ("class:mode", "  ◆ 계획 모드 — 다음 요청을 단계별로 진행"))
            from . import updater
            if updater.latest:
                out.append(("class:mode", " · 새 버전 v%s → /update" % updater.latest))
            return out

        def shift_tab():
            order = ["ask", "auto-edit", "full"]
            mode = order[(order.index(self.perms.mode) + 1) % 3 if self.perms.mode in order else 0]
            self.perms.mode = mode
            if self.bridge:
                try:
                    self.bridge.set_meta(sid=self.sid, mode=mode)
                except Exception:
                    pass

        ui.TUI["hints"] = hints
        ui.TUI["shift_tab"] = shift_tab

    def _banner(self) -> None:
        user = (self.auth or {}).get("user", "")
        print()
        ui.box("", [
            ui.accent("✻") + " " + ui.bold("LMW 에 오신 것을 환영합니다!") + ui.dim("  v" + __version__),
            "",
            ui.dim("  /help 도움말 · /mode 권한 · /model 모델"),
            "",
            ui.dim("  cwd: ") + str(self.root),
            ui.dim("  모델: ") + "%s  (%s, %dK)" % (self.cfg.model, _server_label(self.cfg), self.cfg.context_tokens // 1024),
            ui.dim("  계정: ") + (user or "-"),
        ], "38;2;217;122;74")
        self._check_model()

    def _check_model(self) -> None:
        try:
            models = self.client.list_models()
        except ModelError as e:
            ui.warn(str(e))
            ui.info("/server 로 서버 주소를 바꿀 수 있습니다")
            return
        if self.cfg.model not in models and not any(m.startswith(self.cfg.model + ":") for m in models):
            ui.warn("모델 '%s' 이(가) 서버에 없습니다 — 선택하세요" % self.cfg.model)
            self.pick_model()

    @staticmethod
    def _is_question(text: str) -> bool:
        t = text.strip()
        if re.search(r"(만들어|구현|작성해|고쳐|수정해|추가해|바꿔|build|create|make|implement|fix|add)", t, re.I) \
                and not t.endswith(("?", "？")):
            return False
        return t.endswith(("?", "？")) or (bool(QUESTION_START.match(t)) and len(t) < 200)

    # ------------------------------------------------------------- commands
    WEB_SESSION_BLOCKED = ("/exit", "/quit", "/q", "/logout", "/update", "/setup", "/watch", "/web")

    def run_command(self, line: str) -> Optional[str]:
        """A /command typed in the terminal or sent from the website; its output is also shown on the website."""
        from .events import emit
        cmd = line.split()[0].lower()
        if self.background and cmd in self.WEB_SESSION_BLOCKED:
            emit("notice", level="warn", text="%s 는 컴퓨터의 터미널 세션에서만 쓸 수 있습니다" % cmd)
            return None
        if cmd == "/update" and self.background is False and self.bridge:
            emit("command", text=line, output="lmw 를 업데이트하고 다시 시작합니다…")
        if not self.bridge:
            return self._command(line)
        state = {"first": True}

        def show(text: str, waiting: bool) -> None:
            emit("command", text=line if state["first"] else "", output=text, waiting=waiting)
            state["first"] = False
        try:
            with ui.capture(show, silent=self.background):
                result = self._command(line)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            emit("error", text="%s 실패: %s" % (cmd, e))
            return None
        if state["first"]:  # nothing printed: still confirm on the website
            emit("command", text=line, output="완료")
        return result

    def _command(self, line: str) -> Optional[str]:
        cmd, _, arg = line.partition(" ")
        arg = arg.strip()
        cmd = cmd.lower()
        if cmd in ("/exit", "/quit", "/q"):
            return "exit"
        if cmd in ("/help", "/h", "/?"):
            self._help()
        elif cmd == "/mode":
            if arg in MODE_LABELS:
                self._remote_control("mode", arg)
            else:
                i = ui.menu("권한 모드", [(MODE_LABELS[m], MODE_HINTS[m]) for m in MODE_LABELS],
                            list(MODE_LABELS).index(self.perms.mode))
                if i >= 0:
                    self._remote_control("mode", list(MODE_LABELS)[i])
        elif cmd == "/effort":
            if arg in EFFORT_LABELS:
                self._remote_control("effort", arg)
            else:
                i = ui.menu("생각 수준", [(EFFORT_LABELS[m], EFFORT_HINTS[m]) for m in EFFORT_LABELS],
                            list(EFFORT_LABELS).index(self.effort))
                if i >= 0:
                    self._remote_control("effort", list(EFFORT_LABELS)[i])
        elif cmd in ("/new", "/clear"):
            self.new_session()
        elif cmd == "/compact":
            if not self.agent or not self.agent.compact(manual=True):
                ui.info("요약할 대화가 아직 없습니다")
        elif cmd == "/sessions":
            self.pick_saved_session()
        elif cmd == "/continue":
            self.pick_saved_session(latest=True)
        elif cmd in ("/plan", "/계획", "/deep"):
            if arg in ("off", "취소"):
                self.plan_next = False
                ui.info(ui.dim("계획 모드 취소"))
            elif arg:
                self.handle(arg, route_override="deep")
            else:
                self.plan_next = True
                ui.info(ui.accent("◆ 계획 모드") + ui.dim(" — 다음에 입력하는 요청을 계획 단계에 맞춰 끝까지 진행합니다 (취소: /plan off)"))
        elif cmd == "/engine":
            from .agent import aider_available
            if arg in ("lmw", "aider"):
                if arg == "aider" and not aider_available():
                    ui.warn("Aider 가 없습니다:  pip install aider-chat")
                else:
                    self.engine = arg
                    ui.ok("에이전트 엔진: %s" % arg)
            else:
                ui.info("현재 엔진: %s   (/engine lmw | /engine aider)" % self.engine)
        elif cmd == "/ask":
            self.handle(arg, route_override="agent", readonly=True) if arg else ui.warn("사용법: /ask <질문>")
        elif cmd == "/run":
            self.handle(arg, route_override="agent") if arg else ui.warn("사용법: /run <요청>")
        elif cmd == "/resume":
            self.resume(arg or None)
        elif cmd == "/check":
            ws = Workspace(self.root)
            print(format_findings(run_checks(ws, ws.list_files(), self.cfg.checks, self.cfg.check_timeout)))
        elif cmd == "/files":
            print(Workspace(self.root).tree())
        elif cmd == "/diff":
            self._git_diff()
        elif cmd == "/undo":
            self.undo()
        elif cmd == "/model":
            if arg:
                self.cfg.model = arg
                ui.ok("model → %s" % arg)
            else:
                self.pick_model()
        elif cmd == "/server":
            self._server(arg)
        elif cmd == "/models":
            for m in self.client.list_models():
                print("   - " + m)
        elif cmd == "/memory":
            from . import memory
            a = arg.strip().lower()
            if a in ("on", "켜기", "켜"):
                memory.enabled = True
                ui.ok("기억 켜짐 — 대화를 계정에 저장하고 필요할 때 자동으로 불러옵니다")
            elif a in ("off", "끄기", "꺼"):
                memory.enabled = False
                ui.ok("기억 꺼짐 (이미 저장된 것은 그대로, 지우려면 /memory clear)")
            elif a in ("clear", "삭제", "지우기"):
                n = memory.clear()
                ui.ok("계정의 기억 %d개를 지웠습니다" % n) if n is not None else ui.warn("지우지 못했습니다 (로그인/연결 확인)")
            else:
                n = memory.count()
                ui.info("기억: %s · 계정에 저장된 노트 %s개\n  /memory on · off · clear" % (
                    "켜짐" if memory.enabled else "꺼짐", "?" if n is None else n))
        elif cmd == "/ctx":
            try:
                n = int(arg)
                if n <= self.cfg.max_output_tokens:
                    raise ValueError
                self.cfg.context_tokens = n
                if hasattr(self.client, "forget_cap"):
                    self.client.forget_cap()  # you chose a size: forget what crashes taught
                ui.ok("context → %d tokens" % n)
            except ValueError:
                ui.warn("사용법: /ctx 32768 (max_output_tokens=%d 보다 커야 함)" % self.cfg.max_output_tokens)
        elif cmd == "/rounds":
            if arg.isdigit() and int(arg) >= 1:
                self.cfg.max_review_rounds = int(arg)
                self.cfg.min_review_rounds = min(self.cfg.min_review_rounds, int(arg))
                ui.ok("max review rounds → %s" % arg)
            else:
                ui.warn("사용법: /rounds 5")
        elif cmd == "/skills":
            from . import skillhub
            if skillhub.run_command(arg.split(), log=ui.info) is None:  # /skills add <url> | remove | list
                skills = all_skills(self.cfg.resolved_skills_dir())
                for s in [x for x in skills if not x.library]:
                    mark = "+" if s.name in self.cfg.skills else " "
                    print(" %s %-16s %s" % (mark, s.name, s.description[:90]))
                lib = [x for x in skills if x.library]
                if lib:
                    ui.info("설치한 외부 스킬 %d개 — /skills list · /skills add <GitHub 주소> · /skills remove <이름>" % len(lib))
        elif cmd == "/skill":
            if not arg:
                ui.warn("사용법: /skill web-design")
            elif arg in self.cfg.skills:
                self.cfg.skills.remove(arg)
                ui.ok("skill %s: 자동 선택으로" % arg)
            else:
                self.cfg.skills.append(arg)
                ui.ok("skill %s: 항상 포함" % arg)
        elif cmd == "/auto":
            self.auto = not self.auto
            ui.ok("파일 변경 자동 승인: %s" % ("켜짐" if self.auto else "꺼짐"))
        elif cmd == "/verbose":
            self.cfg.verbose = not self.cfg.verbose
            ui.ok("verbose: %s" % self.cfg.verbose)
        elif cmd == "/setup":
            from .setup import run_wizard
            if run_wizard(self.cfg):
                self.client = ChatClient(self.cfg)
        elif cmd == "/watch":
            if not self.auth:
                ui.warn("로그인되어 있지 않습니다")
            else:
                from .remote_control import watch
                watch(self.auth, exclude=self.bridge.session_id if self.bridge else "")
        elif cmd == "/web":
            if self.auth:
                ui.box("웹에서 보기", [self.auth["hub"], "같은 계정으로 로그인하면 이 컴퓨터가 보입니다"])
            else:
                ui.warn("로그인되어 있지 않습니다")
        elif cmd == "/update":
            from . import updater
            from .events import emit
            if updater.update():
                emit("notice", level="info", text="업데이트 완료 (v%s) — lmw 를 다시 시작합니다. 잠시 후 새 세션으로 연결됩니다"
                     % updater._installed_version())
                for w in self.workers:
                    w.save_session()
                ui.info("새 버전으로 다시 시작합니다…")
                for w in self.workers:
                    w.stop_event.set()
                self.disconnect_hub()
                updater.restart()
        elif cmd == "/logout":
            from .remote_control import logout
            self.disconnect_hub()
            logout()
            return "exit"
        elif cmd == "/stats":
            self._stats()
        elif cmd == "/statusline":
            from .stats import ALL_FIELDS, configure
            if arg:
                fields = [f.strip() for f in re.split(r"[,\s]+", arg) if f.strip()]
                configure(fields)
                self.cfg.statusline = fields
                ui.ok("상태줄: " + ", ".join(fields))
            else:
                ui.info("사용법: /statusline clock,session,tokens,speed,ttft,duration,calls")
                ui.info("사용 가능: " + ", ".join(ALL_FIELDS))
        elif cmd == "/config":
            for k, v in self.cfg.to_dict().items():
                print("   %-20s %s" % (k, v))
        elif cmd == "/tools":
            self._tools_overview()
        elif cmd == "/mcp":
            from . import mcp
            if mcp.run_command(arg.split() or ["list"], str(self.root), log=ui.info) is None:
                ui.info("사용법: /mcp add <time|fetch|git|memory|…> · /mcp add --defaults · /mcp list · /mcp tools · /mcp remove <이름> · /mcp import <주소>")
        elif cmd in ("/agents", "/cmds"):
            self._docs_command("agents" if cmd == "/agents" else "commands", arg.split())
        elif cmd == "/add":
            from . import skillhub
            skillhub.run_pack_command("add", arg.split(), ui.info)
        elif cmd == "/find":
            from . import skillhub
            skillhub.run_pack_command("find", arg.split(), ui.info)
        elif cmd == "/cmd":
            name, _, rest = arg.partition(" ")
            return self._run_user_command(name, rest)
        elif cmd[1:] in self._user_commands():
            return self._run_user_command(cmd[1:], arg)
        else:
            ui.warn("알 수 없는 명령: %s  (/help)" % cmd)
        return None

    # ----------------------------------------------- imported agents / commands
    def _user_commands(self) -> Dict:
        from . import usercmds
        try:
            return usercmds.load()
        except Exception:
            return {}

    def _run_user_command(self, name: str, args: str) -> Optional[str]:
        from . import usercmds
        cmds = self._user_commands()
        c = cmds.get(name.strip().lower().lstrip("/"))
        if c is None:
            ui.warn("가져온 명령이 없습니다: %s   (/cmds list · /cmds add <GitHub 주소>)" % name)
            return None
        ui.info(ui.dim("↳ /%s%s" % (c.name, (" " + args) if args.strip() else "")))
        self.handle(usercmds.expand(c, args), route_override="agent")
        return None

    def _docs_command(self, kind: str, words: List[str]) -> None:
        from . import skillhub
        skillhub.run_docs_command(kind, words, ui.info)

    def _tools_overview(self) -> None:
        from . import toolbox
        ui.box("도구", toolbox.overview(self.cfg, self.root))

    # ----------------------------------------------------------------- task
    # ------------------------------------------------------------- agent turn
    def _get_agent(self):
        from .agent import Agent
        if self.agent is None:
            self.agent = Agent(self.cfg, self.root, self.client, self.ask_permission, self.perms, self.stop_event)
        self.agent.auto_folder = self.base_mode and self.agent.root == self.base_dir
        self.agent.on_retarget = self._retargeted
        self.agent.interject = self._take_interjections
        self.agent.ask_user_cb = self._ask_user
        return self.agent

    def _retargeted(self, root: Path) -> None:
        """The agent picked a job folder under ~/Documents/lmw: the session lives there from now on."""
        self.root = root
        if self.bridge:
            try:
                self.bridge.set_meta(sid=self.sid, cwd=str(root))
            except Exception:
                pass

    def _take_interjections(self) -> List[str]:
        """Prompts that arrived while a request runs: typed in the terminal or sent from the website."""
        from . import keys
        out = keys.KEYS.take() if (keys.KEYS is not None and not self.background) else []
        if self.bridge:
            inbox = self.bridge.channel(self.sid).inbox
            keep = []
            while True:
                try:
                    item = inbox.get_nowait()
                except Exception:
                    break
                src, text = item if isinstance(item, tuple) else ("web", str(item))
                if src in ("web", "key") and text.strip() and not text.startswith("\x00") and not text.strip().startswith("/"):
                    out.append(text.strip())
                    if src == "web":
                        with ui.remote_muted():
                            print(ui.dim("  ↳ 추가 요청 받음 (웹): ") + text.strip())
                else:
                    keep.append(item)
            for item in keep:
                inbox.put(item)
        return out

    def _start_keys(self):
        """Typing while lmw works (terminal session only, when nothing else reads the keyboard)."""
        from . import keys
        if self.background or keys.KEYS is not None:
            return None
        if self.bridge and not getattr(self.bridge, "tui", False):
            return None  # the bridge's line reader already takes typed lines
        k = keys.KeyReader()
        if not k.start():
            return None
        keys.KEYS = k
        return k

    def _stop_keys(self, k) -> None:
        from . import keys
        if k is None:
            return
        keys.KEYS = None
        left = k.stop()
        for t in k.take():  # typed after the last step: run next, in order
            self.pending.append(t)
        if left.strip():
            ui.TUI["prefill"] = left  # unfinished line goes back into the input box

    def handle(self, text: str, route_override: Optional[str] = None, readonly: bool = False) -> None:
        """One user turn: route by effort, run, and report — like a chat app turn."""
        from .agent import Interrupted, route, run_aider, turn_stats
        from .events import emit
        from .stats import STATS
        emit("user", text=text)
        if self.plan_next and not route_override:
            self.plan_next = False
            route_override = "deep"
        kind = route_override or route(text, self.effort)
        if not self.titled:
            self._title = text.strip().replace("\n", " ")[:60]
        if self.bridge and not self.titled:
            self.bridge.set_meta(sid=self.sid, title=text.strip().replace("\n", " ")[:60])
            self.titled = kind != "chat"  # small talk is only a placeholder title
        if kind == "agent" and self.engine == "aider" and not readonly:
            kind = "aider"
        self.stop_event.clear()
        if self.bridge:
            self.bridge.channel(self.sid).running = True
        from .stats import bind
        bind(self.usage)  # model calls made for this turn are billed to this session
        self.usage.begin_turn()
        retry = False
        keyreader = self._start_keys()
        t0, tin, tout = time.time(), self.usage.prompt_tokens, self.usage.output_tokens
        try:
            if kind == "chat":
                self._get_agent().chat(text)
            elif kind == "deep":
                self.task(text)
            elif kind == "aider":
                if self.perms.mode == "ask" and self.ask_permission({
                        "id": "paider%d" % int(t0), "tool": "aider", "title": "Aider 로 이 폴더의 파일 수정",
                        "detail": str(self.root), "danger": False}) == "deny":
                    emit("notice", level="warn", text="취소했습니다")
                else:
                    run_aider(self.cfg, self.root, text, self.stop_event)
            else:
                self._get_agent().run(text, self.effort, readonly=readonly)
        except (Interrupted, KeyboardInterrupt):
            emit("notice", level="warn", text="중지했습니다")
        except ModelError as e:
            emit("error", text=str(e))
            if "멈췄습니다" in str(e) or "메모리 부족" in str(e):
                retry = self._offer_other_server()
        except Exception as e:  # a failing turn must never close lmw
            emit("error", text="%s: %s" % (type(e).__name__, e))
        finally:
            self._stop_keys(keyreader)
            self.usage.end_turn()
            try:
                self.save_session()  # closed sessions can be continued later (/sessions, website)
            except Exception:
                pass
            if self.bridge:
                self.bridge.channel(self.sid).running = False
            if not retry:
                emit("turn_end", stats=turn_stats(t0, tin, tout, self.usage), session=self.usage.line())
        if retry:  # switched to another model server: run the same request again
            self.handle(text, route_override, readonly)

    def ask_permission(self, req: Dict) -> str:
        """Ask the user (terminal or website) before an important action. Returns allow/always/deny."""
        from .events import emit
        from . import tui
        if not self.background and tui.available():
            return self._ask_permission_menu(req)
        emit("permission", **req)
        answers = {"y": "allow", "yes": "allow", "": "allow", "ㅛ": "allow", "a": "always", "ㅁ": "always",
                   "always": "always", "n": "deny", "no": "deny", "ㅜ": "deny"}
        while True:
            try:
                line = self.read(ui.yellow("  허용할까요? [Y]es / [a]lways / [n]o > "))
            except EOFError:
                line = "n"
            by = "terminal"
            if line.startswith(PERM_PREFIX):
                pid, _, decision = line[len(PERM_PREFIX):].partition(":")
                if pid != req["id"] or decision not in ("allow", "always", "deny"):
                    continue
                by = "web"
            elif line.startswith(CTL_PREFIX):
                self.pending.append(line)
                continue
            elif line.strip().lower() in answers:
                decision = answers[line.strip().lower()]
            else:
                self.pending.append(line)  # a new prompt typed while waiting: run it afterwards
                ui.info(ui.dim("(요청을 대기열에 넣었습니다 — 먼저 위 권한에 답해 주세요)"))
                continue
            emit("permission_result", id=req["id"], decision=decision, by=by)
            return decision

    def _ask_permission_menu(self, req: Dict) -> str:
        """Claude-style arrow-key permission menu; the website can answer it too."""
        from .events import emit, diff_preview
        from . import tui
        ui.TUI["choose_active"] = True
        try:
            emit("permission", **req)  # web gets the card; the terminal shows the menu below
        finally:
            ui.TUI["choose_active"] = False
        tool = str(req.get("tool", ""))
        lines = [ui.bold(str(req.get("title", "")))]
        if req.get("detail") and not req.get("diff"):
            lines += ["  " + l for l in str(req["detail"]).splitlines()[:8]]
        lines += diff_preview(str(req.get("diff") or ""), 12)
        if req.get("danger"):
            lines.append(ui.yellow("⚠ 위험할 수 있는 작업입니다"))
        lines += ["", "계속할까요?" if tool in ("bash", "server") else "이 변경을 적용할까요?"]
        again = "예, 이 세션에서 이 명령은 다시 묻지 않기" if tool == "bash" else \
            "예, 바꾸고 다시 시도" if tool == "server" else "예, 이 세션에서 편집은 다시 묻지 않기"
        decisions = ["allow", "always", "deny"]

        def accept(item):
            text = item[1] if isinstance(item, tuple) else str(item)
            if text.startswith(PERM_PREFIX):
                pid, _, d = text[len(PERM_PREFIX):].partition(":")
                if pid == req["id"] and d in decisions:
                    return decisions.index(d)
                return -1  # stale click: drop it
            return None

        ch = self.bridge.channel(self.sid) if self.bridge else None
        from . import keys
        with keys.paused():
            idx, src = tui.choose(lines, ["예", again, "아니요 (다르게 하라고 알려주기)"],
                                  external=getattr(ch, "inbox", None), accept_external=accept)
        if idx < 0:
            idx = 2
        decision = decisions[idx]
        emit("permission_result", id=req["id"], decision=decision, by="web" if src == "web" else "terminal")
        return decision

    def _publish_update(self, latest: str) -> None:
        """Tell the website that this computer can update lmw."""
        from . import __version__
        if self.bridge:
            self.bridge.set_meta(sid=self.sid, version=__version__, latest=latest)

    def _publish_models(self) -> None:
        """Tell the website which models this computer's server has (for its model menu)."""
        def run():
            try:
                models = self.client.list_models()
            except Exception:
                return
            self._models = list(models)[:200]
            if self.bridge:
                self.bridge.set_meta(sid=self.sid, models=self._models, model=self.cfg.model)
                for w in self.workers:
                    self.bridge.set_meta(sid=w.sid, models=self._models)
        threading.Thread(target=run, daemon=True).start()

    def _all_shells(self) -> List["Shell"]:
        main = self.main_shell if getattr(self, "main_shell", None) else self
        return [main] + list(main.workers)

    def _preload(self) -> None:
        try:
            if self.client.load_model(self.cfg.model):
                self._warn_memory(self.cfg.model)
        except Exception:
            pass

    def _warn_memory(self, name: str) -> None:
        from .events import emit
        try:
            msg = self.client.memory_warning(name)
        except Exception:
            msg = ""
        if msg:
            emit("notice", level="warn", text=msg)

    def switch_model(self, old: str, new: str) -> None:
        """Load the newly selected model and unload the previous one (if no other session still uses it)."""
        from .events import emit
        if old == new:
            return
        in_use = {s.cfg.model for s in self._all_shells()}

        sid, bg = self.sid or "", self.background

        def run():
            from .events import set_context
            set_context(sid, bg)  # notices go to the session that switched
            t0 = time.time()
            try:
                if old and old not in in_use:
                    self.client.unload_model(old)
                emit("notice", level="info", text="모델 불러오는 중: %s" % new)
                if self.client.load_model(new):
                    emit("notice", level="info", text="모델 준비됨: %s (%.0f초)%s" % (
                        new, time.time() - t0, " · 이전 모델 %s 내림" % old if old and old not in in_use else ""))
                    self._warn_memory(new)
            except Exception as e:
                emit("notice", level="warn", text="모델 불러오기 실패: %s" % e)
        threading.Thread(target=run, daemon=True).start()

    def _remote_control(self, action: str, value: str) -> None:
        from .events import emit
        if action == "model" and value.strip():
            name = value.strip()
            old = self.cfg.model
            self.cfg.model = name  # next model call uses it; the conversation is kept
            self.switch_model(old, name)
            if self.bridge:
                self.bridge.set_meta(sid=self.sid, model=name)
                if not self.background:
                    self.bridge.model = name
            emit("notice", level="info", text="모델 변경: %s" % name)
            models = getattr(self, "_models", None) or []
            if models and name not in models and not any(m.startswith(name + ":") for m in models):
                emit("notice", level="warn", text="'%s' 은(는) 서버 모델 목록에 없습니다 — 이름을 확인하세요" % name)
            return
        if action == "mode" and value in ("ask", "auto-edit", "full"):
            self.perms.mode = value
            if self.bridge:
                self.bridge.set_meta(sid=self.sid, mode=value)
            emit("notice", level="info", text="권한 모드: %s" % MODE_LABELS[value])
        elif action == "effort" and value in ("auto", "low", "medium", "high"):
            self.effort = value
            if self.bridge:
                self.bridge.set_meta(sid=self.sid, effort=value)
            emit("notice", level="info", text="생각 수준: %s" % EFFORT_LABELS[value])

    # ------------------------------------------------ saved conversations
    def session_key(self) -> str:
        if self.sid:
            return self.sid
        if self.bridge:
            return self.bridge.session_id
        if not getattr(self, "_local_key", None):
            self._local_key = "local-%d" % int(time.time() * 1000)
        return self._local_key

    def save_session(self) -> None:
        from . import sessions
        history = self.agent.history if self.agent else []
        if not history and not self.chat:
            return
        sessions.save(self.session_key(), {
            "title": getattr(self, "_title", "") or "새 세션", "cwd": str(self.root), "model": self.cfg.model,
            "created": self.usage.started, "history": history, "chat": self.chat[-40:],
            "done_tasks": self.done_tasks[-20:],
            "usage": {"prompt_tokens": self.usage.prompt_tokens, "output_tokens": self.usage.output_tokens,
                      "calls": self.usage.calls, "work_seconds": self.usage.work_seconds},
        })

    def restore_session(self, data: Dict) -> None:
        """Continue a saved conversation in this session (the model sees the earlier messages)."""
        from .events import emit
        agent = self._get_agent()
        agent.history = list(data.get("history") or [])
        self.chat = list(data.get("chat") or [])
        self.done_tasks = list(data.get("done_tasks") or [])
        self._title = data.get("title") or ""
        self.titled = True
        if self.bridge and self._title:
            self.bridge.set_meta(sid=self.sid, title="↻ " + self._title[:58])
        n = len(agent.history) + len(self.chat)
        where = "" if os.path.normcase(str(data.get("cwd", ""))) == os.path.normcase(str(self.root)) else \
            " (원래 폴더: %s)" % data.get("cwd", "")
        emit("notice", level="info", text="이전 세션 '%s' 을(를) 이어서 합니다 — 메시지 %d개%s" % (self._title, n, where))
        last = [m for m in agent.history if m.get("role") == "user" and not str(m.get("content", "")).startswith("<tool_result")]
        if last:
            emit("notice", level="info", text="마지막 요청: " + str(last[-1]["content"])[:200])

    def pick_saved_session(self, latest: bool = False) -> None:
        from . import sessions
        cur = self.session_key()
        items = [d for d in sessions.listing(str(self.root)) if d.get("key") != cur]
        if not items:
            ui.info("이 폴더에서 이어서 할 지난 세션이 없습니다")
            return
        if latest:
            self.restore_session(items[0])
            return
        i = ui.menu("이어서 할 세션", [((d.get("title") or "새 세션")[:40],
                                        "%s · %s" % (sessions.ago(d.get("updated", 0)), d.get("model", ""))) for d in items[:15]], 0)
        if i >= 0:
            self.restore_session(items[i])

    def new_session(self) -> None:
        from .events import emit
        self.agent = None
        if self.base_mode:
            self.root = self.base_dir  # the next job gets a new folder
        self.chat.clear()
        self.done_tasks.clear()
        self.titled = False
        self.usage.reset()  # a new session starts counting from zero
        self._title = ""
        self._local_key = None
        if self.bridge:
            try:
                self.bridge.new_session()
            except Exception as e:
                ui.warn("새 세션을 Hub 에 만들지 못했습니다: %s" % e)
        emit("notice", level="info", text="새 세션을 시작했습니다")

    # ------------------------------------------------- sessions opened from the web
    def open_web_session(self, resume: str = "") -> None:
        """'새 세션' on the website: host one more session in THIS process (like Claude Code)."""
        from .remote_control import Bridge
        if not self.bridge:
            return
        try:
            ch = self.bridge.new_session(background=True)
        except Exception as e:
            ui.warn("웹 새 세션을 만들지 못했습니다: %s" % e)
            return
        import copy
        w = Shell(copy.copy(self.cfg), self.base_dir if self.base_mode else self.root, self.auth)  # own config + client: the web can switch its model
        w.bridge, w.sid, w.background = self.bridge, ch.sid, True
        w.client = copy.copy(self.client)  # same server settings, but this session's own model
        w.client.cfg = w.cfg
        w.main_shell = self
        ch.usage = w.usage  # its own token/time totals
        w.perms.mode, w.effort, w.engine = self.perms.mode, self.effort, self.engine
        w.read = lambda prompt="": Bridge.read_channel(ch, prompt)
        ch.on_interrupt = w.stop_event.set
        ch.on_control = w._remote_control
        self.bridge.set_meta(sid=ch.sid, mode=w.perms.mode, effort=w.effort, model=w.cfg.model,
                             models=getattr(self, "_models", None),
                             commands=[[c, d] for c, d, _ in COMMANDS if c not in Shell.WEB_SESSION_BLOCKED])
        self.workers.append(w)
        with ui.remote_muted():
            print(ui.dim("\n⇢ [웹 세션] 웹에서 새 세션이 열렸습니다 (이 터미널은 그대로 사용하세요)"))
        if resume:
            from . import sessions
            data = sessions.load(resume)
            if data:
                from .events import set_context
                set_context(ch.sid, background=True)
                w.restore_session(data)
                set_context("", False)
            else:
                from .events import emit, set_context
                set_context(ch.sid, background=True)
                emit("notice", level="warn", text="이 컴퓨터에 저장된 이전 대화를 찾지 못했습니다 — 새 세션으로 시작합니다")
                set_context("", False)
        threading.Thread(target=w.serve_channel, args=(ch,), daemon=True).start()

    def close_web_session(self, ch) -> None:
        """'세션 닫기' on the website for a session hosted here: end it (its history stays)."""
        from .events import emit
        self.stop_event.set()
        emit("notice", level="info", text="세션을 닫았습니다 — 기록은 남아 있고 '이어서 하기' 로 계속할 수 있습니다")
        self.save_session()
        if self.bridge:
            self.bridge.flush(ended=True, only=ch)
            ch.closed = True
        main = getattr(self, "main_shell", None)
        if main and self in main.workers:
            main.workers.remove(self)
        with ui.remote_muted():
            print(ui.dim("⇢ [웹 세션] 웹에서 세션을 닫았습니다"))

    def serve_channel(self, ch) -> None:
        from .events import set_context
        set_context(ch.sid, background=True)
        ui.set_thread_reader(self.read)  # menus of /commands are answered from the website
        while not ch.closed:
            text = self.pending.pop(0) if self.pending else self.read("")
            if text == CTL_PREFIX + "close_session":
                self.close_web_session(ch)
                return
            if not text or text.startswith("\x00"):
                continue  # late permission clicks / controls with nothing waiting
            try:
                if text.strip().startswith("/"):
                    self.run_command(text.strip())
                    continue
                self.handle(text.strip())
            except Exception as e:  # never kill the worker thread
                from .events import emit
                emit("error", text="세션 오류: %s" % e)

    def task(self, request: str) -> None:
        ctx = "\n".join("- " + t for t in self.done_tasks[-5:])
        pipe = Pipeline(self.cfg, self.root, request=request, client=self.client,
                        ask=self._ask_user, approve=self._approve, session_context=ctx)
        pipe.quiet = True  # one line per stage, then the result — not every phase's details
        self.last_run = pipe
        state = pipe.run()
        self.done_tasks.append(request.strip().replace("\n", " ")[:300])
        if state.get("status") == "done":
            ui.ok("완료 — 이어서 수정 요청을 하거나 /undo 로 되돌릴 수 있습니다")
        else:
            ui.warn("일부 기준이 아직 통과하지 못했습니다. 위 보고서를 확인하고 추가 요청을 보내세요")

    def resume(self, run_id: Optional[str]) -> None:
        runs = self.root / ".lmw" / "runs"
        if not run_id:
            done = sorted(p.name for p in runs.glob("*") if (p / "state.json").is_file()) if runs.is_dir() else []
            if not done:
                ui.warn("이어서 할 작업이 없습니다")
                return
            run_id = done[-1]
        pipe = Pipeline(self.cfg, self.root, run_id=run_id, client=self.client,
                        ask=self._ask_user, approve=self._approve)
        if pipe.state["stage"] == "done":
            ui.info("마지막 작업(%s)은 이미 끝났습니다" % run_id)
            return
        self.last_run = pipe
        pipe.run()

    def _ask_user(self, question: str) -> str:
        try:
            return self.read("  ? %s\n    > " % question)
        except EOFError:
            return ""

    def _approve(self, blocks: List[FileBlock]) -> List[FileBlock]:
        if self.auto or self.perms.mode in ("auto-edit", "full") or "edit" in self.perms.always:
            return blocks
        ws = Workspace(self.root)
        accepted = []
        for b in blocks:
            old = ws.read(b.path)
            new = b.content if b.kind == "file" else (apply_edits(old, b.edits)[0] if old is not None else None)
            if new is None:
                accepted.append(b)  # let the workspace report the error
                continue
            if old is None:
                summary = "새 파일, %d줄" % new.count("\n")
            else:
                diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm=""))
                plus = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
                minus = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
                if not plus and not minus:
                    continue
                summary = "+%d -%d" % (plus, minus)
            while True:
                try:
                    ans = self.read("  %s %s (%s)  [Y]es / [n]o / [d]iff / [a]ll > " % (
                        ui.bold("변경:"), b.path, summary)).strip().lower()
                except EOFError:
                    ans = "y"
                if ans in ("", "y", "yes", "ㅛ"):
                    accepted.append(b)
                    break
                if ans in ("a", "all", "ㅁ"):
                    self.auto = True
                    ui.ok("이번 세션은 자동 승인 (/auto 로 끄기)")
                    accepted.append(b)
                    accepted += [x for x in blocks[blocks.index(b) + 1:]]
                    return accepted
                if ans in ("n", "no", "ㅜ"):
                    break
                if ans in ("d", "diff", "ㅇ"):
                    _print_diff(old or "", new, b.path)
        return accepted

    def undo(self) -> None:
        pipe = self.last_run
        if pipe is None:
            runs = self.root / ".lmw" / "runs"
            done = sorted(p for p in runs.glob("*") if (p / "state.json").is_file()) if runs.is_dir() else []
            if not done:
                ui.warn("되돌릴 작업이 없습니다")
                return
            pipe = Pipeline(self.cfg, self.root, run_id=done[-1].name, client=self.client)
        ws = pipe.ws
        backup = pipe.run_dir / "backup"
        restored, removed = [], []
        for rel in ws.touched:
            src = backup / rel
            dst = self.root / rel
            if src.is_file():
                shutil.copy2(src, dst)
                restored.append(rel)
            elif rel in ws.created and dst.is_file():
                dst.unlink()
                removed.append(rel)
        for r in restored:
            ui.ok("복원 " + r)
        for r in removed:
            ui.ok("삭제 " + r)
        if not restored and not removed:
            ui.info("되돌릴 변경이 없습니다")
        pipe.state["touched"] = []
        ws.touched, ws.created = [], []
        pipe.save()
        self.last_run = None
        if self.done_tasks:
            self.done_tasks.pop()

    def _help(self) -> None:
        lines = ["그냥 입력하면 작업 요청 → 생각·계획·구현·검토/수정을 거쳐 끝까지 완성",
                 "? 로 끝나면 질문 → 파일을 읽고 바로 답변", ""]
        group = ""
        for c, d, g in COMMANDS:
            if g != group:
                lines.append("[%s]" % g)
                group = g
            lines.append("  %-12s %s" % (c, d))
        ui.box("도움말", lines)

    def pick_model(self) -> None:
        """Numbered picker of the models installed on the server."""
        try:
            models = [m for m in self.client.list_models() if m]
        except ModelError as e:
            ui.err(str(e))
            return
        if not models:
            ui.warn("서버에 설치된 모델이 없습니다 (예: ollama pull qwen2.5-coder:14b)")
            return
        print()
        for i, m in enumerate(models, 1):
            mark = ui.green(" ◀ 현재") if m == self.cfg.model else ""
            print("   %2d) %s%s" % (i, m, mark))
        try:
            ans = ui.read_line("  모델 번호 또는 이름 (Enter = 유지) > ").strip()
        except EOFError:
            return
        if not ans:
            return
        choice = models[int(ans) - 1] if ans.isdigit() and 1 <= int(ans) <= len(models) else ans
        old = self.cfg.model
        self.cfg.model = choice
        self.switch_model(old, choice)
        if self.bridge:
            self.bridge.set_meta(sid=self.sid, model=choice)
            self.bridge.model = choice
        ui.ok("model → %s" % choice)
        self._save_choice()

    def _offer_other_server(self) -> bool:
        """Ollama keeps crashing: if another model server is already running here (e.g. vLLM holding the GPU),
        offer to switch to it and retry. True = switched."""
        from .servers import detect
        from .client import ChatClient
        cur = self.cfg.base_url.rstrip("/").replace("/v1", "")
        for srv in detect():
            if srv.base_url.rstrip("/").replace("/v1", "") == cur or srv.key == "ollama":
                continue
            try:
                models = ChatClient(type(self.cfg)(provider=srv.provider, base_url=srv.base_url)).list_models()
            except Exception:
                continue
            if not models:
                continue
            ans = self.ask_permission({
                "id": "psrv%d" % int(time.time()), "tool": "server", "danger": False,
                "title": "이 컴퓨터에서 %s 가 이미 모델을 실행 중입니다 — 그 서버로 바꾸고 다시 시도할까요?" % srv.label,
                "detail": "%s · 모델: %s" % (srv.base_url, ", ".join(models[:3]))})
            if ans == "deny":
                return False
            self.cfg.base_url, self.cfg.provider, self.cfg.model = srv.base_url, srv.provider, models[0]
            self.client = ChatClient(self.cfg)
            if self.agent:
                self.agent.client = self.client
            if self.bridge:
                self.bridge.set_meta(sid=self.sid, model=self.cfg.model, models=list(models)[:200])
                self.bridge.model = self.cfg.model
            from .events import emit
            emit("notice", level="info", text="모델 서버를 %s (%s) 로 바꿨습니다 — 다시 시도합니다" % (srv.label, self.cfg.model))
            return True
        return False

    def _server(self, arg: str) -> None:
        """/server <address> — another PC, another port or a cloud OpenAI-compatible API, in one line."""
        from . import connect
        if not arg.strip():
            ui.info("지금: %s (%s)" % (self.cfg.base_url, self.cfg.provider))
            ui.info("바꾸려면 주소만 입력하세요 (Enter = 취소)")
            for ex, what in (("192.168.0.10", "다른 PC (포트 자동 탐색)"), ("192.168.0.10:1234", "다른 PC의 특정 포트"),
                             (":8000", "이 PC의 다른 포트"), ("lmstudio · vllm · ollama", "이름만"),
                             ("openai · openrouter · groq …", "클라우드 (API 키만 물어봅니다)"),
                             ("https://내주소/v1 [API키]", "그 밖의 OpenAI 호환 주소")):
                print("     %-30s %s" % (ex, ui.dim(what)))
            try:
                arg = ui.read_line("  서버 > ").strip()
            except EOFError:
                return
            if not arg:
                return
        ok, msg = connect.apply(self.cfg, arg, ask_key=lambda: ui.read_line("  API 키 (붙여넣기) > "), log=lambda t: ui.info(ui.dim(t)))
        if not ok:
            ui.err(msg)
            return
        if hasattr(self.client, "reset_server"):
            self.client.reset_server()
        ui.ok("서버 → " + msg)
        self.pick_model()

    def _save_choice(self) -> None:
        """Remember model/server in lmw.config.json of this folder if one exists."""
        import json
        from .config import find_config_file
        f = find_config_file(self.root)
        if not f:
            return
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data.update({"model": self.cfg.model, "base_url": self.cfg.base_url, "provider": self.cfg.provider})
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            ui.info("저장됨: %s" % f)
        except (OSError, ValueError):
            pass

    def _stats(self) -> None:
        from .stats import STATS, fmt_duration, fmt_tokens
        c = STATS.last
        approx = "" if not STATS.calls else (" (일부 추정치)" if STATS.estimated else " (서버 실측)")
        rows = [
            ("현재 시간", time.strftime("%Y-%m-%d %H:%M:%S")),
            ("작업 시간", fmt_duration(time.time() - STATS.session_start)),
            ("모델 호출", "%d회" % STATS.calls),
            ("총 토큰", "%s%s" % (fmt_tokens(STATS.prompt_tokens + STATS.output_tokens), approx)),
            ("  입력", fmt_tokens(STATS.prompt_tokens)),
            ("  출력", fmt_tokens(STATS.output_tokens)),
        ]
        if c:
            rows += [
                ("마지막 출력 속도", "%.1f tok/s" % c.speed),
                ("마지막 첫 토큰", "%.2fs" % c.ttft if c.ttft is not None else "-"),
                ("마지막 응답 시간", "%.1fs" % c.duration),
            ]
        for k, v in rows:
            print("   %-16s %s" % (k, v))

    def _git_diff(self) -> None:
        if not (self.root / ".git").exists() or not shutil.which("git"):
            ui.warn("git 저장소가 아닙니다 — /files 로 확인하세요")
            return
        r = subprocess.run(["git", "diff", "--stat"], cwd=str(self.root), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        print(r.stdout or "(변경 없음)")

    # ------------------------------------------------------------------ ask
    def ask(self, question: str) -> None:
        ws = Workspace(self.root)
        skills = select_skills(all_skills(self.cfg.resolved_skills_dir()), question, self.cfg.skills)
        guide = "\n\n".join(s.body for s in skills if not s.always)
        system = ASK_SYSTEM % (language_rule(question, self.cfg.language), ws.tree())
        if guide:
            system += "\n# Expert guidance\n" + truncate_to_tokens(guide, self.cfg.input_budget() // 3)
        self.chat.append({"role": "user", "content": question})
        read_files: Dict[str, str] = {}
        for _ in range(4):
            budget = self.cfg.input_budget() - estimate_tokens(system)
            history = _trim_history(self.chat, budget)
            progress = ui.Progress(self.cfg.verbose)
            res = self.client.chat([{"role": "system", "content": system}] + history, on_token=progress)
            progress.done()
            answer = strip_reasoning(res.text).strip()
            wanted = [w.strip().strip("`") for w in _READ.findall(answer)]
            wanted = [w for w in wanted if w not in read_files][:5]
            if not wanted:
                self.chat.append({"role": "assistant", "content": answer})
                if not self.cfg.verbose:
                    print("\n" + answer)
                return
            parts = []
            for w in wanted:
                text = ws.read(w)
                ui.info("📄 읽는 중: " + w)
                read_files[w] = text or ""
                parts.append("=== FILE: %s ===\n%s\n=== END FILE ===" % (
                    w, truncate_to_tokens(text, budget // 3) if text is not None else "(file not found)"))
            self.chat.append({"role": "assistant", "content": answer})
            self.chat.append({"role": "user", "content": "\n\n".join(parts) + "\n\nNow answer the question."})
        ui.warn("파일을 너무 많이 요청해서 중단했습니다")


def _trim_history(history: List[Dict[str, str]], budget: int) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    used = 0
    for m in reversed(history):
        t = estimate_tokens(m["content"])
        if used + t > budget:
            if not out:  # always keep the latest message, trimmed
                out.append({"role": m["role"], "content": tail_tokens(m["content"], budget)})
            break
        out.append(m)
        used += t
    out.reverse()
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _print_diff(old: str, new: str, path: str) -> None:
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), "a/" + path, "b/" + path, lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            print(ui.green(line))
        elif line.startswith("-") and not line.startswith("---"):
            print(ui.red(line))
        else:
            print(line)


def _server_label(cfg: Config) -> str:
    from .servers import SERVERS
    for x in SERVERS:
        if x.base_url.rstrip("/") == cfg.base_url.rstrip("/"):
            return x.label
    return cfg.base_url


def run_shell(cfg: Config, workspace: Path, auth: Optional[Dict[str, str]] = None) -> int:
    return Shell(cfg, workspace, auth).loop()
