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
        with self._lock:
            with ui.remote_muted():  # the website gets the structured event, not this printout
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


def render(e: Event, verbose: bool = False) -> None:
    """Terminal rendering (one line per action; details only in verbose mode or on the web)."""
    t = e["type"]
    if t == "thinking":
        secs = e.get("seconds")
        label = "✻ 생각함" + (" (%.1f초)" % secs if isinstance(secs, (int, float)) and secs else "")
        print(ui.dim(label))
        if verbose and e.get("text"):
            print(ui.dim(_indent(e["text"])))
    elif t == "assistant":
        print()
        print(str(e.get("text", "")).rstrip())
    elif t == "tool":
        print(ui.bold("● ") + ui.bold(str(e.get("title") or e.get("name"))))
    elif t == "tool_result":
        mark = ui.green("⎿ ") if e.get("ok") else ui.red("⎿ ✗ ")
        print("  " + mark + str(e.get("summary", "")))
        if verbose and e.get("output"):
            print(ui.dim(_indent(str(e["output"])[:3000])))
    elif t == "permission":
        lines = [str(e.get("title", ""))]
        if e.get("detail"):
            lines.append(str(e["detail"])[:300])
        if e.get("danger"):
            lines.append("⚠ 위험할 수 있는 작업입니다")
        ui.box("권한 요청", lines, "33")
    elif t == "permission_result":
        word = {"allow": "허용", "always": "항상 허용", "deny": "거부"}.get(str(e.get("decision")), str(e.get("decision")))
        by = {"web": " (웹)", "auto": " (자동)", "terminal": ""}.get(str(e.get("by")), "")
        print("  " + (ui.red("⎿ " + word + by) if e.get("decision") == "deny" else ui.green("⎿ " + word + by)))
    elif t == "phase":
        ui.stepper(int(e.get("index", 0) or 0), str(e.get("detail", "")))
    elif t == "notice":
        level = e.get("level")
        (ui.warn if level == "warn" else ui.err if level == "error" else ui.info)(str(e.get("text", "")))
    elif t == "error":
        ui.err(str(e.get("text", "")))
    elif t == "turn_end":
        if e.get("stats"):
            print(ui.dim("  " + str(e["stats"])))
    # "user" is what the person typed; it is already on screen.
