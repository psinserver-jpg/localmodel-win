"""Saved conversations, so a closed session (or yesterday's work) can be continued.

Each session is saved after every turn to ~/.lmw/sessions/<id>.json: the conversation the model
sees, earlier task requests, totals, the folder and the model. `/sessions` and `/continue` load one
back; the website's "이어서 하기" asks the running lmw to open a new session with it.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

MAX_MESSAGES = 80  # newest messages kept per session
MAX_CHARS = 400_000


def folder() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "sessions"


def _safe(key: str) -> str:
    return "".join(c for c in key if c.isalnum() or c in "-_")[:64] or "session"


def save(key: str, data: Dict) -> None:
    msgs = list(data.get("history") or [])[-MAX_MESSAGES:]
    while msgs and sum(len(str(m.get("content", ""))) for m in msgs) > MAX_CHARS:
        msgs.pop(0)
    data = dict(data, history=msgs, key=key, updated=time.time())
    d = folder()
    try:
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / (_safe(key) + ".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(d / (_safe(key) + ".json"))
    except OSError:
        pass


def load(key: str) -> Optional[Dict]:
    try:
        return json.loads((folder() / (_safe(key) + ".json")).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def listing(cwd: Optional[str] = None, limit: int = 30) -> List[Dict]:
    """Saved sessions, newest first (only this folder's when cwd is given)."""
    out = []
    try:
        files = list(folder().glob("*.json"))
    except OSError:
        return []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not d.get("history") and not d.get("chat"):
            continue
        if cwd and os.path.normcase(str(d.get("cwd", ""))) != os.path.normcase(str(cwd)):
            continue
        out.append(d)
    out.sort(key=lambda d: d.get("updated", 0), reverse=True)
    return out[:limit]


def ago(ts: float) -> str:
    s = max(0, time.time() - (ts or 0))
    if s < 60:
        return "방금"
    if s < 3600:
        return "%d분 전" % (s // 60)
    if s < 86400:
        return "%d시간 전" % (s // 3600)
    return "%d일 전" % (s // 86400)
