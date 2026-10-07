"""GPU memory: warn when the model does not fit (it then crashes or runs slowly on the CPU)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def usage() -> Optional[Dict]:
    """{"name", "used", "total", "free"} in MiB for the first NVIDIA GPU, plus "apps" using the most memory."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=8).stdout.strip().splitlines()
        name, used, total = [x.strip() for x in out[0].split(",")][:3]
        info = {"name": name, "used": int(float(used)), "total": int(float(total))}
        info["free"] = info["total"] - info["used"]
        apps: List[Dict] = []
        out = subprocess.run([exe, "--query-compute-apps=process_name,used_memory", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=8).stdout.strip().splitlines()
        for line in out:
            parts = [x.strip() for x in line.rsplit(",", 1)]
            if len(parts) == 2 and parts[1].replace(".", "").isdigit():
                apps.append({"name": parts[0].replace("\\", "/").split("/")[-1], "mem": int(float(parts[1]))})
        info["apps"] = sorted(apps, key=lambda a: -a["mem"])[:3]
        return info
    except (OSError, subprocess.SubprocessError, IndexError, ValueError):
        return None


def describe(info: Optional[Dict]) -> str:
    if not info:
        return ""
    gb = lambda mib: "%.1fGB" % (mib / 1024)
    text = "%s: %s / %s 사용 중 (남은 메모리 %s)" % (info["name"], gb(info["used"]), gb(info["total"]), gb(info["free"]))
    if info.get("apps"):
        text += " · 많이 쓰는 프로그램: " + ", ".join("%s %s" % (a["name"], gb(a["mem"])) for a in info["apps"])
    return text


def low(info: Optional[Dict], need_mib: int = 1536) -> bool:
    return bool(info) and info["free"] < need_mib


def ollama_log_errors(max_lines: int = 6) -> str:
    """The last error lines from Ollama's own log (why its model process stopped)."""
    import os
    import re
    cands = []
    if os.name == "nt":
        cands.append(Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "server.log")
    cands += [Path.home() / ".ollama" / "logs" / "server.log", Path("/tmp/ollama.log")]
    for f in cands:
        try:
            if not f.is_file():
                continue
            with open(f, "rb") as fh:
                fh.seek(max(0, f.stat().st_size - 200_000))
                lines = fh.read().decode("utf-8", "replace").splitlines()
        except OSError:
            continue
        pat = re.compile(r"error|panic|fatal|fault|exception|out of memory|CUDA|cudaMalloc|terminated|exit status|failed", re.I)
        hits = [l.strip() for l in lines if pat.search(l) and "level=DEBUG" not in l]
        if hits:
            return "\n".join("    " + h[-220:] for h in hits[-max_lines:]) + "\n    (로그: %s)" % f
        return ""
    return ""
