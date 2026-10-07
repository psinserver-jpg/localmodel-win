"""Skills and sub-agents served by LMW Hub (psin.ai.kr) instead of living in this repository.

lmw keeps a local copy in ~/.lmw/hub/{skills,agents}. It is refreshed in the background at start
(at most every 6 hours) and with `lmw sync`; only files whose hash changed are downloaded, and files
removed from the hub are removed here. Offline, the last copy keeps working.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Optional

from . import __version__, netutil

HUB = os.environ.get("LMW_HUB", "https://psin.ai.kr").rstrip("/")
INTERVAL = 6 * 3600
_lock = threading.Lock()


def home() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "hub"


def skills_dir() -> Path:
    return home() / "skills"


def agents_dir() -> Path:
    return home() / "agents"


def _get(path: str, timeout: float = 20) -> bytes:
    req = urllib.request.Request(HUB + path, headers={"User-Agent": "lmw-cli/%s" % __version__})
    with netutil.urlopen(req, timeout=timeout) as r:
        return r.read()


def _safe(rel: str) -> bool:
    p = Path(rel)
    return bool(rel) and not p.is_absolute() and ".." not in p.parts and p.parts[0] in ("skills", "agents")


def sync(force: bool = False, log: Optional[Callable[[str], None]] = None) -> Dict[str, int]:
    """Bring ~/.lmw/hub up to date. Returns {"downloaded": n, "removed": n, "total": n}; raises on network errors."""
    log = log or (lambda s: None)
    with _lock:
        root = home()
        stamp = root / ".synced"
        if not force and stamp.is_file() and time.time() - stamp.stat().st_mtime < INTERVAL:
            return {"downloaded": 0, "removed": 0, "total": -1}
        index = json.loads(_get("/api/content/index").decode("utf-8"))
        files = {f["path"]: f for f in index.get("files", []) if _safe(str(f.get("path", "")))}
        down = 0
        for rel, meta in files.items():
            dest = root / rel
            if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == meta.get("sha256"):
                continue
            data = _get("/api/content/file?path=" + urllib.parse.quote(rel), 30)
            if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
                log("체크섬 불일치, 건너뜀: %s" % rel)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(data)
            os.replace(tmp, dest)
            down += 1
        removed = 0
        for sub in ("skills", "agents"):
            base = root / sub
            if not base.is_dir():
                continue
            for f in [p for p in base.rglob("*") if p.is_file()]:
                if f.relative_to(root).as_posix() not in files:
                    f.unlink()
                    removed += 1
        root.mkdir(parents=True, exist_ok=True)
        stamp.write_text(str(int(time.time())))
        return {"downloaded": down, "removed": removed, "total": len(files)}


def sync_in_background(on_done: Optional[Callable[[Dict[str, int]], None]] = None, wait_first: float = 0) -> None:
    """Refresh in a thread. On the very first run (nothing downloaded yet) wait up to `wait_first` seconds."""
    def run():
        try:
            res = sync()
        except Exception:
            return
        if on_done and (res["downloaded"] or res["removed"]):
            try:
                on_done(res)
            except Exception:
                pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    if wait_first and not (home() / ".synced").is_file():
        t.join(wait_first)
