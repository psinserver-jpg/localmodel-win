"""Interactive LMW agent shell — `lmw` with no arguments.

Like Claude Code, but built for local models:
- A task message runs the full 8-phase workflow in the current folder.
- A question (or /ask) gets a direct answer; the model may read project files first.
- Every file change is shown and needs approval (toggle with /auto).
- /undo restores the files changed by the last task.
"""

from __future__ import annotations

import difflib
import time
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__, ui
from .checks import format_findings, run_checks
from .client import ChatClient, ModelError, strip_reasoning
from .config import Config
from .parse import FileBlock, apply_edits
from .pipeline import Pipeline
from .skills import load_skills, select_skills
from .textutil import estimate_tokens, language_rule, tail_tokens, truncate_to_tokens
from .workspace import Workspace

try:  # arrow keys + history on macOS/Linux; Windows consoles already have line editing
    import readline  # noqa: F401
except ImportError:
    pass

# (command, description, group) — drives /help, the "/" menu and Tab completion
COMMANDS = [
    ("/run", "작업 요청 (8단계로 끝까지 완성)", "작업"),
    ("/ask", "질문하기 (파일을 읽고 답변)", "작업"),
    ("/resume", "중단된 작업 이어하기", "작업"),
    ("/undo", "마지막 작업 되돌리기", "작업"),
    ("/files", "프로젝트 파일 보기", "작업"),
    ("/check", "자동 검사 실행", "작업"),
    ("/diff", "git 변경 요약", "작업"),
    ("/model", "모델 선택", "모델"),
    ("/server", "모델 서버 변경 (LM Studio, vLLM, 다른 PC…)", "모델"),
    ("/setup", "처음 설정 다시 하기", "모델"),
    ("/ctx", "컨텍스트 크기 (/ctx 32768)", "모델"),
    ("/skills", "스킬 목록", "모델"),
    ("/skill", "스킬 항상 포함 토글 (/skill web-design)", "모델"),
    ("/auto", "파일 변경 자동 승인 켜기/끄기", "설정"),
    ("/rounds", "최대 검토/수정 횟수 (/rounds 5)", "설정"),
    ("/verbose", "모델 출력 실시간 보기", "설정"),
    ("/stats", "시간 · 토큰 · 속도 통계", "설정"),
    ("/statusline", "상태줄 항목 변경", "설정"),
    ("/config", "현재 설정 보기", "설정"),
    ("/clear", "대화 기록 지우기", "설정"),
    ("/watch", "다른 컴퓨터의 lmw 화면 보기·조작", "계정"),
    ("/web", "이 화면을 웹에서 보는 주소", "계정"),
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
        self.auto = False
        self.chat: List[Dict[str, str]] = []  # question-mode history
        self.done_tasks: List[str] = []  # earlier task requests this session
        self.last_run: Optional[Pipeline] = None
        self.client = ChatClient(cfg)

    # ------------------------------------------------------------------ main
    bridge = None

    def loop(self) -> int:
        _setup_completion()
        self._banner()
        self.connect_hub()
        print(ui.dim("  Enter = 메뉴 · / = 전체 명령 · Tab = 명령 자동완성 · 질문은 ? 로 끝내기"))
        try:
            return self._loop()
        finally:
            self.disconnect_hub()

    def connect_hub(self) -> None:
        """Always-on remote control: publish this session to the user's Hub account."""
        from .remote_control import Bridge
        if not self.auth or self.bridge:
            return
        try:
            self.bridge = Bridge(self.auth, "lmw", str(self.root), self.cfg.model)
        except Exception as e:
            ui.warn("Hub 연결 실패 (%s) — 이 컴퓨터에서만 작업합니다" % e)
            return
        self.bridge.start()
        ui.ok("이 화면이 실시간으로 공유됩니다 — 웹(%s) 또는 다른 컴퓨터의 lmw(/watch)에서 %s 계정으로 보기·입력"
              % (self.auth["hub"], self.auth.get("user", "")))

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
                print()
                ui.status()
                line = ui.read_line(ui.prompt_label("lmw") + " ").strip()
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print()
                continue
            if not line:
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
                    if self._command(line) == "exit":
                        return 0
                elif self._is_question(line):
                    self.ask(line)
                else:
                    self.task(line)
            except KeyboardInterrupt:
                ui.warn("중단됨 — /resume 으로 이어서 할 수 있습니다")
            except ModelError as e:
                ui.err(str(e))
                ui.info("진행 상황은 저장됨 — /resume")
            except (FileNotFoundError, ValueError) as e:
                ui.err(str(e))

    def _banner(self) -> None:
        user = (self.auth or {}).get("user", "")
        print()
        ui.box("LMW %s · Local Model Workflow" % __version__, [
            "👤 계정   " + (user or "-"),
            "🤖 모델   %s  (%s, %dK)" % (self.cfg.model, _server_label(self.cfg), self.cfg.context_tokens // 1024),
            "📁 폴더   %s" % self.root,
        ])
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
    def _command(self, line: str) -> Optional[str]:
        cmd, _, arg = line.partition(" ")
        arg = arg.strip()
        cmd = cmd.lower()
        if cmd in ("/exit", "/quit", "/q"):
            return "exit"
        if cmd in ("/help", "/h", "/?"):
            self._help()
        elif cmd == "/ask":
            self.ask(arg) if arg else ui.warn("사용법: /ask <질문>")
        elif cmd == "/run":
            self.task(arg) if arg else ui.warn("사용법: /run <요청>")
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
        elif cmd == "/ctx":
            try:
                n = int(arg)
                if n <= self.cfg.max_output_tokens:
                    raise ValueError
                self.cfg.context_tokens = n
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
            for s in load_skills(self.cfg.resolved_skills_dir()):
                mark = "+" if s.name in self.cfg.skills else " "
                print(" %s %-16s %s" % (mark, s.name, s.description[:90]))
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
        elif cmd == "/clear":
            self.chat.clear()
            self.done_tasks.clear()
            ui.ok("대화 기록을 지웠습니다")
        else:
            ui.warn("알 수 없는 명령: %s  (/help)" % cmd)
        return None

    # ----------------------------------------------------------------- task
    def task(self, request: str) -> None:
        ctx = "\n".join("- " + t for t in self.done_tasks[-5:])
        pipe = Pipeline(self.cfg, self.root, request=request, client=self.client,
                        ask=self._ask_user, approve=self._approve, session_context=ctx)
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

    @staticmethod
    def _ask_user(question: str) -> str:
        try:
            return ui.read_line("  ? %s\n    > " % question)
        except EOFError:
            return ""

    def _approve(self, blocks: List[FileBlock]) -> List[FileBlock]:
        if self.auto:
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
                    ans = ui.read_line("  %s %s (%s)  [Y]es / [n]o / [d]iff / [a]ll > " % (
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
        self.cfg.model = choice
        ui.ok("model → %s" % choice)
        self._save_choice()

    def _server(self, arg: str) -> None:
        """/server <url> [ollama|openai] — switch model server (e.g. another PC on the LAN)."""
        if not arg:
            ui.info("%s (%s)" % (self.cfg.base_url, self.cfg.provider))
            ui.info("사용법: /server http://192.168.0.10:11434 ollama   |   /server http://localhost:1234/v1 openai")
            return
        parts = arg.split()
        self.cfg.base_url = parts[0]
        if len(parts) > 1 and parts[1] in ("ollama", "openai"):
            self.cfg.provider = parts[1]
        elif parts[0].rstrip("/").endswith("/v1"):
            self.cfg.provider = "openai"
        ui.ok("server → %s (%s)" % (self.cfg.base_url, self.cfg.provider))
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
        skills = select_skills(load_skills(self.cfg.resolved_skills_dir()), question, self.cfg.skills)
        guide = "\n\n".join(s.body for s in skills if not s.always)
        system = ASK_SYSTEM % (language_rule(question), ws.tree())
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
