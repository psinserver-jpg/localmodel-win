"""Session statistics and the live status line.

Tracks wall-clock session time, total prompt/output tokens, output speed, time to
first token and response time. Uses exact counts from the server when it reports them
(Ollama native, OpenAI-style `usage`), otherwise a conservative estimate (marked ~).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .textutil import estimate_tokens

ALL_FIELDS = ["clock", "session", "tokens", "speed", "ttft", "duration", "calls"]


def fmt_duration(sec: float) -> str:
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return "%dh%02dm%02ds" % (h, m, s)
    if m:
        return "%dm%02ds" % (m, s)
    return "%ds" % s


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return "%.2fM" % (n / 1_000_000)
    if n >= 1000:
        return "%.1fK" % (n / 1000)
    return str(n)


@dataclass
class CallStats:
    start: float = 0.0
    first_token: Optional[float] = None
    end: Optional[float] = None
    out_chars: int = 0
    out_text_tokens: int = 0  # estimate while streaming
    prompt_tokens: int = 0
    output_tokens: int = 0
    exact: bool = False
    gen_seconds: Optional[float] = None  # pure generation time if the server reports it

    @property
    def ttft(self) -> Optional[float]:
        return None if self.first_token is None else self.first_token - self.start

    @property
    def duration(self) -> float:
        return (self.end or time.time()) - self.start

    @property
    def speed(self) -> float:
        toks = self.output_tokens or self.out_text_tokens
        if self.gen_seconds:
            return toks / self.gen_seconds if self.gen_seconds > 0 else 0.0
        if self.first_token is None:
            return 0.0
        span = (self.end or time.time()) - self.first_token
        return toks / span if span > 0.3 else 0.0


@dataclass
class Stats:
    session_start: float = field(default_factory=time.time)
    prompt_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    estimated: bool = False
    current: Optional[CallStats] = None
    last: Optional[CallStats] = None
    fields: List[str] = field(default_factory=lambda: list(ALL_FIELDS))
    _buf: List[str] = field(default_factory=list)

    # ------------------------------------------------------------ recording
    def begin(self, messages: List[Dict[str, str]]) -> None:
        c = CallStats(start=time.time())
        c.prompt_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        self.current = c
        self._buf = []

    def token(self, piece: str) -> None:
        c = self.current
        if c is None:
            return
        if c.first_token is None:
            c.first_token = time.time()
        c.out_chars += len(piece)
        self._buf.append(piece)
        if len(self._buf) >= 16:  # re-estimate in batches; cheap enough
            c.out_text_tokens += estimate_tokens("".join(self._buf))
            self._buf = []

    def finish(self, usage: Optional[Dict[str, float]] = None) -> None:
        c = self.current
        if c is None:
            return
        c.end = time.time()
        if self._buf:
            c.out_text_tokens += estimate_tokens("".join(self._buf))
            self._buf = []
        if usage and usage.get("completion_tokens"):
            c.output_tokens = int(usage["completion_tokens"])
            if usage.get("prompt_tokens"):
                c.prompt_tokens = int(usage["prompt_tokens"])
            c.exact = True
            if usage.get("gen_seconds"):
                c.gen_seconds = float(usage["gen_seconds"])
        else:
            c.output_tokens = c.out_text_tokens
            self.estimated = True
        self.prompt_tokens += c.prompt_tokens
        self.output_tokens += c.output_tokens
        self.calls += 1
        self.last, self.current = c, None

    def abort(self) -> None:
        self.current = None
        self._buf = []

    # ------------------------------------------------------------- display
    @property
    def total_tokens(self) -> int:
        live = self.current.out_text_tokens + self.current.prompt_tokens if self.current else 0
        return self.prompt_tokens + self.output_tokens + live

    def parts(self) -> List[str]:
        c = self.current or self.last
        out = []
        for f in self.fields:
            if f == "clock":
                out.append("🕒 " + time.strftime("%H:%M:%S"))
            elif f == "session":
                out.append("⏱ " + fmt_duration(time.time() - self.session_start))
            elif f == "tokens":
                approx = "~" if self.estimated or self.current else ""
                out.append("Σ %s%s tok (in %s / out %s)" % (
                    approx, fmt_tokens(self.total_tokens), fmt_tokens(self.prompt_tokens + (self.current.prompt_tokens if self.current else 0)),
                    fmt_tokens(self.output_tokens + (self.current.out_text_tokens if self.current else 0))))
            elif f == "speed":
                out.append("⚡ %.1f tok/s" % (c.speed if c else 0.0))
            elif f == "ttft":
                t = c.ttft if c else None
                out.append("1st %s" % ("%.1fs" % t if t is not None else ("…" if self.current else "-")))
            elif f == "duration":
                out.append("⌛ %.1fs" % (c.duration if c else 0.0))
            elif f == "calls":
                out.append("#%d" % (self.calls + (1 if self.current else 0)))
        return out

    def line(self) -> str:
        return " │ ".join(self.parts())


STATS = Stats()


def configure(fields: Optional[List[str]]) -> None:
    if fields:
        valid = [f for f in fields if f in ALL_FIELDS]
        STATS.fields = valid or list(ALL_FIELDS)
