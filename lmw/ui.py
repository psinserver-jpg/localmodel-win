"""Console output helpers (Windows-safe: UTF-8 and ANSI colors where supported)."""

from __future__ import annotations

import re
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
    return accent(_c("1", "> ")) if text == "lmw" else _c("1;35", text + " ❯")


def accent(text: str) -> str:
    """LMW orange (truecolor; Windows Terminal, Ghostty and modern consoles)."""
    return "\033[38;2;217;122;74m%s\033[0m" % text if _COLOR else text


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
        for tok in re.findall(r"\x1b\[[0-9;]*m|.", l, re.S):  # wrap by display width; keep color codes whole
            if not tok.startswith("\x1b") and dwidth(cur + tok) > inner:
                out.append(cur + ("\x1b[0m" if "\x1b" in cur else ""))
                cur = ""
            cur += tok
        out.append(cur)
    top = ("╭─ " + title + " " + "─" * max(0, inner - dwidth(title) - 1) + "╮") if title else \
        "╭" + "─" * (inner + 2) + "╮"
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
    m = _re.match(r"^(\d)/8 ([A-Z ]+?)(?: — (.*))?$", title)
    if m:
        from .events import emit  # deep-mode phases become structured events (stepper on the web)
        emit("phase", index=int(m.group(1)), name=m.group(2).strip(), detail=m.group(3) or "")
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
    """Print the status line once (dim). Not mirrored as text: the hub gets it as live status."""
    line = prefix + status_line()
    with remote_muted():
        print(_c("2", line[: _width() - 6]), flush=True)


class Progress:
    """Live status line (clock, session time, tokens, speed, first-token, duration) while
    the model works, refreshed twice a second. In verbose mode the text streams instead
    and the status line is printed when the answer is complete."""

    def __init__(self, verbose: bool, show_status: bool = True):
        self.verbose = verbose
        self.show_status = show_status
        self._t0 = time.time()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        # only the terminal's own session draws the live line (web-opened sessions run in worker threads)
        if not verbose and sys.stdout.isatty() and threading.current_thread() is threading.main_thread():
            self._thread = threading.Thread(target=self._tick, daemon=True)
            self._thread.start()

    GLYPHS = "·✢✳✶✻✽✻✶✳✢"

    def _render(self) -> None:
        from .stats import STATS, fmt_tokens
        self._n = getattr(self, "_n", 0) + 1
        c = STATS.current
        secs = int(time.time() - self._t0)
        toks = c.out_text_tokens if c else 0
        if c is None or c.first_token is None:
            verb = "준비 중…"  # prompt processing / model loading, not thinking
        elif self._thinking:
            verb = "생각하는 중…"
        else:
            verb = "작성 중…"
        g = self.GLYPHS[self._n % len(self.GLYPHS)]
        line = "%s %s (%ds · ↓ %s 토큰 · Ctrl+C 로 중지)" % (g, verb, secs, fmt_tokens(toks))
        head, rest = g + " " + verb, line[len(g) + 1 + len(verb):]
        pad = " " * max(0, _width() - 2 - dwidth(line))
        with self._lock:
            sys.stdout.write("\r" + accent(head) + _c("2", rest) + pad + "\r")
            sys.stdout.flush()

    def _tick(self) -> None:
        while not self._stop.wait(0.5):
            self._render()

    _thinking = False

    def __call__(self, piece: str) -> None:
        if "<think>" in piece:
            self._thinking = True
        if "</think>" in piece:
            self._thinking = False
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
        if self.show_status:
            status("  ✓ ")


# ------------------------------------------------------------- input routing
# When remote control is active, input can come from the keyboard OR the web.
_input_hook = None  # callable(prompt) -> str, installed by remote_control.Bridge


def set_input_hook(hook) -> None:
    global _input_hook
    _input_hook = hook


# Set by the shell: slash commands, hint line and Shift+Tab handler for the Claude-style input box.
TUI = {"commands": [], "hints": lambda: [], "shift_tab": None, "choose_active": False}


def read_line(prompt: str = "", main: bool = False) -> str:
    """main=True: the big input box (lmw ❯). Otherwise a one-line question."""
    if _input_hook is not None:
        try:
            return _input_hook(prompt, main)
        except TypeError:  # hooks that only take a prompt
            return _input_hook(prompt)
    if main:
        from . import tui
        if tui.available():
            return tui.input_box(TUI["commands"], TUI["hints"], TUI["shift_tab"])[1]
    return input(prompt)


# ------------------------------------------------------------- remote mirroring control
# Text printed inside `remote_muted()` is not copied to the hub as raw terminal output
# (used for things the website receives as structured events, and for noisy status lines).
_tls = threading.local()


class remote_muted:
    def __enter__(self):
        _tls.mute = getattr(_tls, "mute", 0) + 1
        return self

    def __exit__(self, *exc):
        _tls.mute = getattr(_tls, "mute", 1) - 1
        return False


def is_remote_muted() -> bool:
    return getattr(_tls, "mute", 0) > 0
