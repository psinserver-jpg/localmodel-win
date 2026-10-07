"""Typing while lmw works: lines typed during a request are added to it (Claude-Code-style).

While a request runs, a background reader collects keystrokes. The line being typed is shown on the
status (spinner) line; Enter queues it. The agent picks queued lines up before its next step, in order.
Paused while a menu or a question owns the keyboard.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import time
from contextlib import contextmanager
from typing import List, Optional


class KeyReader:
    def __init__(self) -> None:
        self.buf = ""
        self.lines: "queue.Queue[str]" = queue.Queue()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._old = None

    # ------------------------------------------------------------- lifecycle
    def start(self) -> bool:
        if self._thread or not (sys.stdin.isatty() and sys.stdout.isatty()):
            return False
        if os.name != "nt":
            try:
                import termios
                import tty
                fd = sys.stdin.fileno()
                self._old = termios.tcgetattr(fd)
                tty.setcbreak(fd)  # keys one by one; Ctrl+C still interrupts
            except Exception:
                return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> str:
        """Stop reading; returns the unfinished line (to prefill the next prompt)."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None
        self._restore()
        left, self.buf = self.buf, ""
        return left

    def _restore(self) -> None:
        if self._old is not None and os.name != "nt":
            try:
                import termios
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old)
            except Exception:
                pass
        self._old = None

    @contextmanager
    def paused(self):
        """A menu / question reads the keyboard itself meanwhile."""
        self._paused.set()
        old = self._old
        if old is not None and os.name != "nt":
            self._restore()
        try:
            yield
        finally:
            if old is not None and os.name != "nt" and self._thread:
                try:
                    import termios
                    import tty
                    self._old = termios.tcgetattr(sys.stdin.fileno())
                    tty.setcbreak(sys.stdin.fileno())
                except Exception:
                    pass
            self._paused.clear()

    # ----------------------------------------------------------------- input
    def take(self) -> List[str]:
        out = []
        while True:
            try:
                out.append(self.lines.get_nowait())
            except queue.Empty:
                return out

    def _key(self, ch: str) -> None:
        if ch in ("\r", "\n"):
            if self.buf.strip():
                self.lines.put(self.buf.strip())
                from . import ui
                with ui.remote_muted():
                    sys.stdout.write("\r\x1b[2K")
                    print(ui.dim("  ↳ 추가 요청 받음: ") + self.buf.strip() + ui.dim("  (다음 단계에서 반영)"))
            self.buf = ""
        elif ch in ("\x08", "\x7f"):
            self.buf = self.buf[:-1]
        elif ch == "\x15":  # Ctrl+U
            self.buf = ""
        elif ch == "\x1b":
            pass
        elif ch.isprintable():
            self.buf += ch

    def _run(self) -> None:
        if os.name == "nt":
            import msvcrt
            while not self._stop.is_set():
                if self._paused.is_set() or not msvcrt.kbhit():
                    time.sleep(0.05)
                    continue
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # arrows / function keys: two codes, ignore
                    msvcrt.getwch()
                    continue
                self._key(ch)
            return
        import select
        fd = sys.stdin.fileno()
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.05)
                continue
            try:
                r, _, _ = select.select([fd], [], [], 0.1)
            except (OSError, ValueError):
                return
            if not r or self._paused.is_set():
                continue
            try:
                data = os.read(fd, 64).decode("utf-8", "replace")
            except OSError:
                return
            if data.startswith("\x1b") and len(data) > 1:
                continue  # arrow keys etc.
            for ch in data:
                self._key(ch)


KEYS: Optional[KeyReader] = None  # the reader of the running request (main terminal session only)


@contextmanager
def paused():
    if KEYS is not None:
        with KEYS.paused():
            yield
    else:
        yield
