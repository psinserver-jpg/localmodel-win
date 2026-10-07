"""Self-update: `/update` in lmw, or `lmw update` in a shell.

Uses `git pull` when lmw was installed with git, otherwise downloads the latest zip from GitHub
and copies it over the install (files are overwritten, nothing else is deleted).
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from . import netutil
from . import __version__, ui

REPO = "psinserver-jpg/localmodel-win"
BRANCH = os.environ.get("LMW_BRANCH", "main")
APP = Path(__file__).resolve().parent.parent  # the install folder (contains lmw/, skills/, prompts/)
PARTS = ("lmw", "skills", "agents", "prompts", "README.md", "LICENSE", "install.ps1", "install.sh")

latest: Optional[str] = None  # filled in by check_in_background()


def _get(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "lmw-cli/%s" % __version__})
    with netutil.urlopen(req, timeout=timeout) as r:
        return r.read()


def _ver(v: str) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def remote_version(timeout: float = 5) -> Optional[str]:
    try:
        text = _get("https://raw.githubusercontent.com/%s/%s/lmw/__init__.py" % (REPO, BRANCH), timeout).decode("utf-8")
    except Exception:
        return None
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else None


def check_in_background(on_found=None) -> None:
    """Look for a newer version without slowing down startup (on_found(version) when there is one)."""
    def run():
        global latest
        v = remote_version()
        if v and _ver(v) > _ver(__version__):
            latest = v
            if on_found:
                try:
                    on_found(v)
                except Exception:
                    pass
    threading.Thread(target=run, daemon=True).start()


def _installed_version() -> str:
    try:
        text = (APP / "lmw" / "__init__.py").read_text(encoding="utf-8")
        return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)
    except Exception:
        return __version__


def update() -> bool:
    """Install the latest version. True if files changed."""
    before = _installed_version()
    ui.info("업데이트 확인 중… (%s)" % APP)
    if (APP / ".git").is_dir() and shutil.which("git"):
        r = subprocess.run(["git", "-C", str(APP), "pull", "--ff-only", "-q", "origin", BRANCH],
                           capture_output=True, text=True)
        if r.returncode != 0:
            ui.err("git pull 실패: %s" % (r.stderr.strip() or r.stdout.strip()))
            return False
    else:
        try:
            data = _get("https://github.com/%s/archive/refs/heads/%s.zip" % (REPO, BRANCH), timeout=120)
        except Exception as e:
            ui.err("다운로드 실패: %s" % e)
            return False
        with tempfile.TemporaryDirectory() as tmp:
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
            src = next(Path(tmp).iterdir())
            try:
                for name in PARTS:
                    s = src / name
                    if s.is_dir():
                        shutil.copytree(s, APP / name, dirs_exist_ok=True)
                    elif s.is_file():
                        shutil.copy2(s, APP / name)
            except OSError as e:
                ui.err("파일 복사 실패: %s — 다른 lmw 창을 닫고 다시 시도하세요" % e)
                return False
    _ensure_deps()
    after = _installed_version()
    if after == before:
        ui.ok("최신 파일로 업데이트했습니다 (v%s)" % after)
    else:
        ui.ok("업데이트 완료: v%s → v%s" % (before, after))
    return True


def _ensure_deps() -> None:
    try:
        import prompt_toolkit  # noqa: F401
        return
    except ImportError:
        pass
    ui.info(ui.dim("입력 화면 구성요소(prompt_toolkit) 설치 중…"))
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "--disable-pip-version-check",
                    "prompt_toolkit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restart(args=()) -> None:
    """Run the freshly installed lmw in this same window, then exit with its code."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(APP) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    sys.stdout.flush()
    try:
        rc = subprocess.call([sys.executable, "-m", "lmw", "--here"] + list(args), env=env)
    except KeyboardInterrupt:
        rc = 130
    os._exit(rc)
