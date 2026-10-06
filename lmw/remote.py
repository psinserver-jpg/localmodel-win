"""Work on another computer over SSH.

- lmw ssh HOST          open the LMW agent shell ON the remote machine (lmw must be installed there)
- lmw ssh-install HOST  install/update LMW on the remote machine (git clone + install script)
- lmw tunnel HOST       forward the remote model server to this PC, so local lmw uses its GPU

Uses the system `ssh` client (Windows 10+ ships OpenSSH), so ~/.ssh/config aliases,
keys and ssh-agent all work as usual.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from typing import List

from . import ui

REPO_URL = "https://github.com/psinserver-jpg/localmodel-win.git"


def _ssh_base(host: str, port: int = 0, tty: bool = True) -> List[str]:
    exe = shutil.which("ssh")
    if not exe:
        raise FileNotFoundError("ssh not found. Windows: Settings > Apps > Optional features > OpenSSH Client")
    cmd = [exe]
    if tty:
        cmd.append("-t")  # interactive terminal for the shell, prompts and the live status line
    if port:
        cmd += ["-p", str(port)]
    return cmd + [host]


def remote_command(args: List[str], directory: str, windows: bool) -> str:
    if windows:  # remote default shell is cmd.exe; lmw.bat is on PATH after install.ps1
        quoted = " ".join('"%s"' % a.replace('"', '\\"') if (" " in a or not a) else a for a in args)
        cd = 'cd /d "%s" && ' % directory if directory else ""
        return "%slmw %s" % (cd, quoted)
    inner = "lmw " + " ".join(shlex.quote(a) for a in args)
    if directory:
        inner = "cd %s && %s" % (shlex.quote(directory) if not directory.startswith("~") else directory, inner)
    # login shell so ~/.local/bin from install.sh is on PATH
    return "sh -lc %s" % shlex.quote(inner)


def cmd_ssh(host: str, port: int, directory: str, windows: bool, args: List[str]) -> int:
    cmd = _ssh_base(host, port) + [remote_command(args, directory, windows)]
    ui.info("→ %s 에서 lmw 실행 (종료: /exit)" % host)
    return subprocess.call(cmd)


def cmd_install(host: str, port: int, windows: bool, branch: str, repo: str) -> int:
    if windows:
        ps = (
            "$d = Join-Path $env:USERPROFILE 'localmodel-win'; "
            "if (Test-Path $d) { git -C $d fetch origin %(b)s; git -C $d checkout %(b)s; git -C $d pull origin %(b)s } "
            "else { git clone -b %(b)s %(r)s $d }; "
            "powershell -ExecutionPolicy Bypass -File (Join-Path $d 'install.ps1')"
        ) % {"b": branch, "r": repo}
        remote = 'powershell -NoProfile -Command "%s"' % ps.replace('"', '\\"')
    else:
        sh = (
            'd="$HOME/localmodel-win"; '
            'if [ -d "$d/.git" ]; then git -C "$d" fetch origin %(b)s && git -C "$d" checkout %(b)s && git -C "$d" pull origin %(b)s; '
            'else git clone -b %(b)s %(r)s "$d"; fi && sh "$d/install.sh"'
        ) % {"b": shlex.quote(branch), "r": shlex.quote(repo)}
        remote = "sh -lc %s" % shlex.quote(sh)
    ui.info("→ %s 에 LMW 설치/업데이트 (branch %s)" % (host, branch))
    code = subprocess.call(_ssh_base(host, port) + [remote])
    if code == 0:
        ui.ok("설치 완료 — 이제 실행:  lmw ssh %s" % host)
    return code


def cmd_tunnel(host: str, port: int, local_port: int, remote_port: int) -> int:
    cmd = _ssh_base(host, port, tty=False) + []
    cmd.insert(1, "-N")
    cmd.insert(2, "-L")
    cmd.insert(3, "%d:127.0.0.1:%d" % (local_port, remote_port))
    ui.info("→ %s 의 모델 서버(:%d) 를 이 PC의 localhost:%d 로 연결합니다 (Ctrl+C 로 종료)" % (host, remote_port, local_port))
    ui.info("   다른 터미널에서:  lmw --provider ollama --base-url http://localhost:%d" % local_port)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 0
