"""Project workspace: safe reads/writes, file tree, backups of files we overwrite."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .parse import FileBlock, apply_edits

IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".lmw", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".idea", ".vscode", ".next", ".nuxt",
    "dist", "build", "coverage", ".cache", "target",
}
MAX_TEXT_BYTES = 256_000


class UnsafePathError(ValueError):
    pass


class Workspace:
    def __init__(self, root: Path, backup_dir: Optional[Path] = None):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.backup_dir = backup_dir
        self.touched: List[str] = []  # files written during this run, in order

    # ----------------------------------------------------------------- paths
    def resolve(self, rel: str) -> Path:
        rel = rel.replace("\\", "/").strip()
        if not rel or rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
            raise UnsafePathError("absolute or empty path not allowed: %r" % rel)
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise UnsafePathError("path escapes the workspace: %r" % rel)
        if ".lmw" in Path(rel).parts or ".git" in Path(rel).parts:
            raise UnsafePathError("refusing to write inside .lmw/.git: %r" % rel)
        return p

    def rel(self, p: Path) -> str:
        return p.resolve().relative_to(self.root).as_posix()

    # ----------------------------------------------------------------- reads
    def iter_files(self) -> Iterable[Path]:
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            parts = p.relative_to(self.root).parts
            if any(part in IGNORE_DIRS for part in parts[:-1]):
                continue
            yield p

    def list_files(self) -> List[str]:
        return [self.rel(p) for p in self.iter_files()]

    def read(self, rel: str) -> Optional[str]:
        try:
            p = self.resolve(rel)
        except UnsafePathError:
            return None
        if not p.is_file() or p.stat().st_size > MAX_TEXT_BYTES:
            return None
        data = p.read_bytes()
        if b"\x00" in data[:4096]:
            return None
        for enc in ("utf-8", "utf-8-sig", "cp949", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return None

    def tree(self, max_entries: int = 200) -> str:
        files = self.list_files()
        if not files:
            return "(empty — this is a new project)"
        lines = []
        for f in files[:max_entries]:
            size = (self.root / f).stat().st_size
            lines.append("- %s (%d bytes)" % (f, size))
        if len(files) > max_entries:
            lines.append("- ... and %d more files" % (len(files) - max_entries))
        return "\n".join(lines)

    def snapshot_hash(self, files: Optional[List[str]] = None) -> str:
        h = hashlib.sha256()
        for f in sorted(files if files is not None else self.list_files()):
            h.update(f.encode())
            h.update((self.read(f) or "").encode("utf-8", errors="replace"))
        return h.hexdigest()

    # ---------------------------------------------------------------- writes
    def _backup(self, p: Path) -> None:
        if not self.backup_dir or not p.exists():
            return
        dest = self.backup_dir / self.rel(p)
        if dest.exists():  # keep the ORIGINAL version from before this run
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)

    def write(self, rel: str, content: str) -> None:
        p = self.resolve(rel)
        self._backup(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        # newline="" keeps "\n" as-is on Windows; editors handle LF fine.
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
        r = self.rel(p)
        if r not in self.touched:
            self.touched.append(r)

    def apply_blocks(self, blocks: List[FileBlock]) -> Tuple[List[str], List[str]]:
        """Write FILE blocks and apply EDIT blocks. Returns (changed_paths, problems)."""
        changed, problems = [], []
        for b in blocks:
            try:
                if b.kind == "edit":
                    current = self.read(b.path)
                    if current is None:
                        problems.append("EDIT for %s failed: file does not exist (use a FILE block)" % b.path)
                        continue
                    if not b.edits:
                        problems.append("EDIT for %s contained no SEARCH/REPLACE pairs" % b.path)
                        continue
                    new, failed = apply_edits(current, b.edits)
                    for snippet in failed:
                        problems.append("EDIT for %s: SEARCH text not found:\n%s" % (b.path, snippet))
                    if new != current:
                        self.write(b.path, new)
                        changed.append(b.path)
                else:
                    if not b.closed:
                        problems.append("FILE %s was cut off (no END FILE marker)" % b.path)
                    self.write(b.path, b.content)
                    changed.append(b.path)
            except UnsafePathError as e:
                problems.append(str(e))
        return changed, problems

    def contents_block(self, files: List[str]) -> Dict[str, str]:
        out = {}
        for f in files:
            text = self.read(f)
            if text is not None:
                out[f] = text
        return out
