"""The default place lmw works when you did not choose a folder: ~/Documents/lmw/<name of the job>.

When lmw starts somewhere that is not a project (your home folder, Desktop, Documents, Downloads, the lmw
install folder, ...), each new job gets its own folder under ~/Documents/lmw, named after what you asked for.
Start lmw inside a project folder (or with -w) and it works right there, as before.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Callable, Optional

APP = Path(__file__).resolve().parent.parent
_STOP = {"the", "a", "an", "to", "for", "me", "my", "please", "make", "create", "build", "write", "and", "of", "in",
         "만들어줘", "만들어", "해줘", "해주세요", "주세요", "좀", "하나", "그리고", "에서", "으로", "를", "을", "만들자", "하자", "설명해줘", "알려줘", "고쳐줘", "수정해줘", "보여줘", "작성해줘", "만들어주세요"}


def documents_dir() -> Path:
    home = Path.home()
    for cand in (home / "Documents", home / "문서"):
        if cand.is_dir():
            return cand
    if os.name == "nt":  # OneDrive often moves Documents
        up = os.environ.get("USERPROFILE")
        if up and (Path(up) / "OneDrive" / "Documents").is_dir():
            return Path(up) / "OneDrive" / "Documents"
    return home / "Documents"


def base_dir() -> Path:
    env = os.environ.get("LMW_PROJECTS_DIR")
    return Path(env).expanduser() if env else documents_dir() / "lmw"


def ensure_base() -> Path:
    b = base_dir()
    try:
        b.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return b


def is_unchosen(cwd: Path) -> bool:
    """True when lmw was started somewhere that is not a project folder (so it should pick one itself)."""
    if os.environ.get("LMW_NO_AUTO_FOLDER"):
        return False
    try:
        here = cwd.resolve()
    except OSError:
        return False
    home = Path.home().resolve()
    places = {home, home / "Desktop", home / "Documents", home / "Downloads", home / "문서", home / "바탕 화면",
              home / "다운로드", documents_dir(), base_dir(), APP, Path(here.anchor or "/")}
    if sys.platform == "win32":
        places |= {Path(os.environ.get("SystemRoot", "C:\\Windows")), Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32"}
    resolved = set()
    for p in places:
        try:
            resolved.add(p.resolve())
        except OSError:
            pass
    return here in resolved


def clean_name(text: str, limit: int = 40) -> str:
    """A safe folder name from free text (keeps Korean, letters, digits)."""
    t = re.sub(r"[`'\"“”‘’.,!?:;()\[\]{}<>|\\/*]+", " ", text.strip().splitlines()[0] if text.strip() else "")
    t = re.sub(r"[^0-9A-Za-z가-힣_\- ]+", " ", t)
    t = re.sub(r"[\s_]+", "-", t.strip()).strip("-").lower()
    t = t[:limit].strip("-")
    if t.upper() in ("CON", "PRN", "AUX", "NUL") or re.fullmatch(r"(COM|LPT)\d", t.upper() or "x"):
        t += "-project"
    return t


def fallback_name(request: str) -> str:
    words = [w for w in re.findall(r"[0-9A-Za-z가-힣]+", request) if w.lower() not in _STOP]
    return clean_name(" ".join(words[:4])) or "작업"


def name_for(request: str, ask_model: Optional[Callable[[str], str]] = None) -> str:
    """Short folder name for a request: the model summarizes it, a plain word pick is the fallback."""
    name = ""
    if ask_model:
        try:
            name = clean_name(ask_model(request[:600]))
        except Exception:
            name = ""
    if len(name) < 2 or len(name) > 40:
        name = fallback_name(request)
    return name


def make_folder(name: str, base: Optional[Path] = None) -> Path:
    base = base or ensure_base()
    base.mkdir(parents=True, exist_ok=True)
    cand, n = base / name, 2
    while cand.exists():
        cand = base / ("%s-%d" % (name, n))
        n += 1
    cand.mkdir(parents=True)
    return cand
