"""Console output helpers (Windows-safe: UTF-8 and ANSI colors where supported)."""

from __future__ import annotations

import os
import sys
import time

_COLOR = False


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


def banner(title: str) -> None:
    line = "─" * max(10, 60 - len(title))
    print("\n" + _c("1;36", "▶ " + title + " " + line), flush=True)


def info(msg: str) -> None:
    print("  " + msg, flush=True)


def ok(msg: str) -> None:
    print("  " + _c("32", "✔ " + msg), flush=True)


def warn(msg: str) -> None:
    print("  " + _c("33", "! " + msg), flush=True)


def err(msg: str) -> None:
    print("  " + _c("31", "✘ " + msg), file=sys.stderr, flush=True)


class Progress:
    """Live 'generating… N chars' counter, or full streaming when verbose."""

    def __init__(self, verbose: bool):
        self.verbose = verbose
        self.chars = 0
        self.start = time.time()
        self._last = 0.0

    def __call__(self, piece: str) -> None:
        self.chars += len(piece)
        if self.verbose:
            sys.stdout.write(piece)
            sys.stdout.flush()
            return
        now = time.time()
        if now - self._last > 0.25:
            self._last = now
            sys.stdout.write("\r  … generating %d chars (%.0fs)" % (self.chars, now - self.start))
            sys.stdout.flush()

    def done(self) -> None:
        if self.verbose:
            sys.stdout.write("\n")
        else:
            sys.stdout.write("\r" + " " * 50 + "\r")
        sys.stdout.flush()
