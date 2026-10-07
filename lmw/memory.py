"""Long-term memory on your LMW Hub account.

lmw saves what happened (each finished request + answer, and the old messages that /compact throws away)
and looks up the relevant notes by itself when you ask something new, so the context can stay small while
a long job - or a conversation from another day or another computer - is still remembered.

Everything is best effort: offline, logged out or `memory` turned off just means nothing is saved/found.
Secrets (API keys, tokens, passwords) are blanked out before anything leaves the computer.
Turn off with the `memory` setting / LMW_MEMORY=0 or `/memory off`; `/memory clear` deletes it all.
"""

from __future__ import annotations

import os
import queue
import re
import threading
import time
import urllib.parse
from typing import Dict, List, Optional

from . import remote_control as rc

_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{30,}|xox[abprs]-[A-Za-z0-9\-]{10,}"
    r"|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$))")
_ASSIGN = re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|client[_-]?secret|비밀번호)\b(\s*[:=]\s*)(\S{6,})")

enabled = os.environ.get("LMW_MEMORY", "1").lower() not in ("0", "off", "false", "no")
_q: "queue.Queue" = queue.Queue(maxsize=200)
_worker: Optional[threading.Thread] = None
_lock = threading.Lock()


def scrub(text: str) -> str:
    text = _SECRET.sub("[비밀값 제거됨]", text)
    return _ASSIGN.sub(lambda m: m.group(1) + m.group(2) + "[비밀값 제거됨]", text)


def _auth() -> Optional[Dict[str, str]]:
    if not enabled:
        return None
    a = rc.load_auth()
    return a if a and not a.get("offline") else None


def _post_loop() -> None:
    while True:
        item = _q.get()
        batch = [item]
        try:
            while len(batch) < 20:
                batch.append(_q.get_nowait())
        except queue.Empty:
            pass
        by: Dict[tuple, List[Dict]] = {}
        for project, session, it in batch:
            by.setdefault((project, session), []).append(it)
        a = _auth()
        if not a:
            continue
        for (project, session), items in by.items():
            try:
                rc._req("POST", a["hub"].rstrip("/") + "/api/memory",
                        {"project": project, "session": session, "items": items}, a["token"], timeout=15)
            except Exception:
                pass  # offline / older hub: this note is simply not kept


def save(project: str, session: str, text: str, kind: str = "turn") -> None:
    """Queue a note for the hub (returns immediately; never raises)."""
    global _worker
    try:
        text = scrub(" ".join(text.split()) if kind == "note" else text.strip())
        if len(text) < 8 or not _auth():
            return
        with _lock:
            if _worker is None:
                _worker = threading.Thread(target=_post_loop, daemon=True)
                _worker.start()
        _q.put_nowait((str(project), str(session), {"text": text[:4000], "kind": kind, "ts": time.time()}))
    except Exception:
        pass


def save_turn(project: str, session: str, request: str, answer: str) -> None:
    if len(request.strip()) < 6 or len(answer.strip()) < 6:
        return
    save(project, session, "[요청] %s\n[결과] %s" % (request.strip()[:1200], answer.strip()[:2400]))


def save_dropped(project: str, session: str, messages: List[Dict[str, str]]) -> None:
    """Messages that /compact is about to replace with a summary: keep the originals."""
    parts = []
    for m in messages:
        c = str(m.get("content", "")).strip()
        if not c or c.startswith("<tool_result"):
            continue
        parts.append("%s: %s" % ("사용자" if m.get("role") == "user" else "lmw", c[:900]))
    text = "\n".join(parts)
    for i in range(0, len(text), 3500):  # one row per ~3.5k characters
        save(project, session, text[i:i + 3500], "context")


def search(query: str, project: str = "", limit: int = 4, timeout: float = 4) -> List[Dict]:
    a = _auth()
    if not a or len(query.strip()) < 4:
        return []
    try:
        _, d = rc._req("GET", "%s/api/memory/search?q=%s&project=%s&limit=%d" % (
            a["hub"].rstrip("/"), urllib.parse.quote(query[:400]), urllib.parse.quote(project), limit), None, a["token"], timeout)
        return list(d.get("items") or [])
    except Exception:
        return []


def clear(project: str = "") -> Optional[int]:
    a = rc.load_auth()
    if not a:
        return None
    try:
        _, d = rc._req("POST", a["hub"].rstrip("/") + "/api/memory/clear", {"project": project}, a["token"], timeout=15)
        return int(d.get("deleted", 0))
    except Exception:
        return None


def count() -> Optional[int]:
    a = rc.load_auth()
    if not a:
        return None
    try:
        return int(rc._req("GET", a["hub"].rstrip("/") + "/api/memory/stats", None, a["token"], 8)[1].get("count", 0))
    except Exception:
        return None


def prompt_block(query: str, project: str, budget_chars: int = 2400) -> str:
    """The '# Earlier conversations' section for the system prompt ('' when nothing relevant)."""
    if not enabled:
        return ""
    items = search(query, project)
    if not items:
        return ""
    out, used = [], 0
    for it in items:
        when = time.strftime("%Y-%m-%d", time.localtime(float(it.get("ts") or 0)))
        text = str(it.get("text", "")).strip()
        if used + len(text) > budget_chars:
            text = text[: max(0, budget_chars - used)]
        if len(text) < 20:
            break
        out.append("[%s] %s" % (when, text))
        used += len(text)
    if not out:
        return ""
    return ("\n# Earlier conversations (saved on the user's account; use only if relevant, they may be outdated)\n"
            + "\n---\n".join(out) + "\n")
