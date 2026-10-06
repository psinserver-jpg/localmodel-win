"""Console output helpers (Windows-safe: UTF-8 and ANSI colors where supported)."""

from __future__ import annotations

import os
import shutil
import sys
import threading
import time

_COLOR = False
_ANSI_RE = __import__('re').compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def setup_console() -> None:
    global _COLOR
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    if os.name == "nt":
        os.system("")  # enables ANSI escape processing in Windows 10+ consoles
    _COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return "\033[%sm%s\033[0m" % (code, text) if _COLOR else text


def bold(text: str) -> str:
    return _c("1", text)


def green(text: str) -> str:
    return _c("32", text)


def red(text: str) -> str:
    return _c("31", text)


def prompt_label(text: str) -> str:
    return _c("1;35", text + " ❯")


def dim(text: str) -> str:
    return _c("2", text)


def cyan(text: str) -> str:
    return _c("36", text)


def yellow(text: str) -> str:
    return _c("33", text)


def dwidth(text: str) -> int:
    """Display width: Hangul/CJK/emoji take 2 columns."""
    import unicodedata
    w = 0
    for ch in _ANSI_RE.sub("", text):
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") or ord(ch) >= 0x1F300 else 1
    return w


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - dwidth(text))


def box(title: str, lines, color: str = "36") -> None:
    """Rounded box that fits the terminal; long lines are wrapped."""
    inner = min(max([dwidth(title) + 2] + [dwidth(l) for l in lines] + [30]), _width() - 6)
    out = []
    for l in lines:
        cur = ""
        for ch in l:  # wrap by display width (Korean/emoji are 2 columns)
            if dwidth(cur + ch) > inner:
                out.append(cur)
                cur = ""
            cur += ch
        out.append(cur)
    top = "╭─ " + title + " " + "─" * max(0, inner - dwidth(title) - 1) + "╮"
    print(_c(color, top))
    for l in out:
        print(_c(color, "│ ") + _pad(l, inner) + _c(color, " │"))
    print(_c(color, "╰" + "─" * (inner + 2) + "╯"), flush=True)


PHASES = [("THINK", "생각"), ("REVIEW", "이해검토"), ("PLAN", "계획"), ("REVIEW PLAN", "계획검토"),
          ("IMPLEMENT", "구현"), ("REVIEW", "결과검토"), ("FIX", "수정"), ("DELIVER", "보고")]


def stepper(active: int, detail: str = "") -> None:
    """One-line progress: ✔ done ▶ current · pending."""
    parts = []
    for i, (_, ko) in enumerate(PHASES, 1):
        if i < active:
            parts.append(_c("32", "✔" + ko))
        elif i == active:
            parts.append(_c("1;36", "▶" + ko))
        else:
            parts.append(_c("2", "·" + ko))
    print("\n " + " ".join(parts) + ("  " + _c("2", detail) if detail else ""), flush=True)


def banner(title: str) -> None:
    import re as _re
    m = _re.match(r"^(\d)/8 [A-Z ]+?(?: — (.*))?$", title)
    if m:
        stepper(int(m.group(1)), m.group(2) or "")
        return
    print("\n" + _c("1;36", "▶ " + title), flush=True)


def menu(title: str, options, default: int = 0) -> int:
    """Numbered menu. Returns the chosen index, or -1 if cancelled."""
    print()
    print(_c("1", title))
    for i, (label, hint) in enumerate(options, 1):
        mark = _c("36", "›") if i - 1 == default else " "
        print(" %s %s %s %s" % (mark, _c("1;36", "%d)" % i), _pad(label, 24), _c("2", hint)))
    try:
        ans = read_line(_c("2", "  번호 선택 (Enter=%d, q=취소) > " % (default + 1))).strip().lower()
    except EOFError:
        return -1
    if ans in ("q", "ㅂ", "x"):
        return -1
    if not ans:
        return default
    if ans.isdigit() and 1 <= int(ans) <= len(options):
        return int(ans) - 1
    return -1


def info(msg: str) -> None:
    print("  " + msg, flush=True)


def ok(msg: str) -> None:
    print("  " + _c("32", "✔ " + msg), flush=True)


def warn(msg: str) -> None:
    print("  " + _c("33", "! " + msg), flush=True)


def err(msg: str) -> None:
    print("  " + _c("31", "✘ " + msg), file=sys.stderr, flush=True)


def _width() -> int:
    try:
        return shutil.get_terminal_size((100, 20)).columns
    except OSError:
        return 100


def status_line() -> str:
    from .stats import STATS
    return STATS.line()


def status(prefix: str = "  ") -> None:
    """Print the status line once (dim)."""
    line = prefix + status_line()
    print(_c("2", line[: _width() - 6]), flush=True)


class Progress:
    """Live status line (clock, session time, tokens, speed, first-token, duration) while
    the model works, refreshed twice a second. In verbose mode the text streams instead
    and the status line is printed when the answer is complete."""

    def __init__(self, verbose: bool):
        self.verbose = verbose
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        if not verbose and sys.stdout.isatty():
            self._thread = threading.Thread(target=self._tick, daemon=True)
            self._thread.start()

    def _render(self) -> None:
        line = "  ⟳ " + status_line()
        w = _width() - 6  # emoji are double-width in most terminals
        line = line[:w]
        with self._lock:
            sys.stdout.write("\r" + _c("36", line) + " " * max(0, w - len(line)))
            sys.stdout.flush()

    def _tick(self) -> None:
        while not self._stop.wait(0.5):
            self._render()

    def __call__(self, piece: str) -> None:
        if self.verbose:
            sys.stdout.write(piece)
            sys.stdout.flush()

    def done(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
            with self._lock:
                sys.stdout.write("\r" + " " * (_width() - 1) + "\r")
                sys.stdout.flush()
        if self.verbose:
            sys.stdout.write("\n")
        status("  ✓ ")


# ------------------------------------------------------------- input routing
# When remote control is active, input can come from the keyboard OR the web.
_input_hook = None  # callable(prompt) -> str, installed by remote_control.Bridge


def set_input_hook(hook) -> None:
    global _input_hook
    _input_hook = hook


def read_line(prompt: str = "") -> str:
    if _input_hook is not None:
        return _input_hook(prompt)
    return input(prompt)
