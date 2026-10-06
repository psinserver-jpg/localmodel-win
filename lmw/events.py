"""Structured session events.

Everything the agent does is emitted as an event. The terminal renders events in a compact
Claude-Code-like style; the hub bridge forwards the same events to the website, which renders
them as collapsible thinking / tool / permission blocks.

Event types: user, assistant, thinking, tool, tool_result, permission, permission_result,
phase, notice, error, turn_end (and "log" for raw terminal text, produced by the bridge).
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List

from . import ui

Event = Dict[str, object]
Sink = Callable[[Event], None]

TOOL_LABELS = {
    "read_file": "Read", "write_file": "Write", "edit_file": "Edit", "list_dir": "List",
    "glob": "Glob", "grep": "Grep", "bash": "Bash",
}


_ctx = threading.local()


def set_context(session_id: str = "", background: bool = False, title: str = "") -> None:
    """Bind events emitted by this thread to a session (used by sessions opened from the web)."""
    _ctx.sid, _ctx.background, _ctx.title = session_id, background, title


def _short(text: object, n: int = 50) -> str:
    t = str(text or "").replace("\n", " ").strip()
    return t[:n] + ("…" if len(t) > n else "")


def render_background(e: Event) -> None:
    """Terminal view of a web-opened session: one dim line per important moment."""
    t, tag = e["type"], ui.dim("⇢ [웹 세션] ")
    if t == "user":
        print(tag + ui.dim("요청: " + _short(e.get("text"))))
    elif t == "permission":
        print(tag + ui.yellow("권한 요청 — 웹에서 승인하세요: " + _short(e.get("title"))))
    elif t == "turn_end":
        print(tag + ui.dim("완료 " + str(e.get("stats") or "")))
    elif t == "error":
        print(tag + ui.red(_short(e.get("text"), 80)))


class EventBus:
    def __init__(self) -> None:
        self.sinks: List[Sink] = []
        self.verbose = False
        self._lock = threading.Lock()

    def subscribe(self, sink: Sink) -> None:
        self.sinks.append(sink)

    def unsubscribe(self, sink: Sink) -> None:
        if sink in self.sinks:
            self.sinks.remove(sink)

    def emit(self, type_: str, **data) -> Event:
        e: Event = {"type": type_, "ts": time.time(), **data}
        sid = getattr(_ctx, "sid", "")
        if sid:
            e["_sid"] = sid
        with self._lock:
            with ui.remote_muted():  # the website gets the structured event, not this printout
                if getattr(_ctx, "background", False):
                    render_background(e)
                else:
                    render(e, self.verbose)
            for sink in list(self.sinks):
                try:
                    sink(e)
                except Exception:
                    pass
        return e


BUS = EventBus()


def emit(type_: str, **data) -> Event:
    return BUS.emit(type_, **data)


def _indent(text: str, prefix: str = "     ") -> str:
    return "\n".join(prefix + l for l in str(text).splitlines())


def diff_preview(diff: str, max_lines: int = 14) -> List[str]:
    """Claude-style changed-lines view: line numbers, red removals, green additions."""
    import re
    out: List[str] = []
    old_no = new_no = 0
    for line in str(diff or "").splitlines():
        if line.startswith(("---", "+++")):
            continue
        m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
        if m:
            old_no, new_no = int(m.group(1)), int(m.group(2))
            if out:
                out.append(ui.dim("       ⋮"))
            continue
        if line.startswith("-"):
            out.append(ui.red("  %5d - %s" % (old_no, line[1:])))
            old_no += 1
        elif line.startswith("+"):
            out.append(ui.green("  %5d + %s" % (new_no, line[1:])))
            new_no += 1
        else:
            out.append(ui.dim("  %5d   %s" % (new_no, line[1:] if line.startswith(" ") else line)))
            old_no += 1
            new_no += 1
    if len(out) > max_lines:
        rest = len(out) - max_lines
        out = out[:max_lines] + [ui.dim("     … +%d줄" % rest)]
    return out


def render(e: Event, verbose: bool = False) -> None:
    """Terminal rendering in the Claude Code style (details are also on the web)."""
    t = e["type"]
    if t == "thinking":
        secs = e.get("seconds")
        print(ui.dim("✻ 생각함" + (" (%.1f초)" % secs if isinstance(secs, (int, float)) and secs else "")))
        if verbose and e.get("text"):
            print(ui.dim(_indent(e["text"], "  ")))
    elif t == "assistant":
        lines = str(e.get("text", "")).rstrip().splitlines() or [""]
        print()
        print("● " + lines[0])
        for l in lines[1:]:
            print("  " + l)
    elif t == "tool":
        title = str(e.get("title") or e.get("name"))
        name, _, arg = title.partition("(")
        print()
        print(ui.green("● ") + ui.bold(name) + ("(" + arg if arg else ""))
    elif t == "tool_result":
        if not e.get("ok"):
            print("  ⎿  " + ui.red(str(e.get("summary", ""))))
            return
        print("  ⎿  " + str(e.get("summary", "")))
        if e.get("diff"):
            for l in diff_preview(str(e["diff"])):
                print("    " + l)
        elif e.get("output") and (verbose or e.get("_show")):
            out = str(e["output"]).splitlines()
            for l in out[:4]:
                print(ui.dim("     " + l[:200]))
            if len(out) > 4:
                print(ui.dim("     … +%d줄" % (len(out) - 4)))
    elif t == "permission":
        if ui.TUI.get("choose_active"):
            return  # the arrow-key menu shows it
        lines = [str(e.get("title", ""))]
        if e.get("detail"):
            lines.append(str(e["detail"])[:300])
        if e.get("danger"):
            lines.append("⚠ 위험할 수 있는 작업입니다")
        ui.box("권한 요청", lines, "33")
        for l in diff_preview(str(e.get("diff") or ""), 10):
            print("  " + l)
    elif t == "permission_result":
        d = str(e.get("decision"))
        word = {"allow": "허용", "always": "허용 (이 세션에서 다시 묻지 않음)", "deny": "거부"}.get(d, d)
        by = {"web": " · 웹", "auto": " · 자동", "terminal": ""}.get(str(e.get("by")), "")
        print("  ⎿  " + (ui.red(word + by) if d == "deny" else ui.dim(word + by)))
    elif t == "phase":
        i = int(e.get("index", 0) or 0)
        if 1 <= i <= len(ui.PHASES):  # one quiet line per stage; no per-phase thinking/details
            print(ui.dim("  ◆ %d/%d %s" % (i, len(ui.PHASES), ui.PHASES[i - 1][1])))
    elif t == "notice":
        level = e.get("level")
        text = str(e.get("text", ""))
        print(ui.yellow("  ※ " + text) if level == "warn" else ui.red("  ✘ " + text) if level == "error"
              else ui.dim("  ※ " + text))
    elif t == "error":
        print(ui.red("  ✘ " + str(e.get("text", ""))))
    elif t == "turn_end":
        if e.get("stats"):
            print(ui.dim("\n  " + str(e["stats"])))
    # "user" is what the person typed; it is already on screen.
