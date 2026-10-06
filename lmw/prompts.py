"""Prompt templates and budget-aware prompt assembly."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .textutil import estimate_tokens, truncate_to_tokens


class Templates:
    def __init__(self, prompts_dir: Path):
        self.dir = prompts_dir
        self._cache: Dict[str, str] = {}

    def get(self, name: str) -> str:
        if name not in self._cache:
            self._cache[name] = (self.dir / (name + ".md")).read_text(encoding="utf-8")
        return self._cache[name]


_VAR = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


@dataclass
class Slot:
    """A variable in a template. Lower `priority` numbers are trimmed first when over budget."""
    text: str
    priority: int = 50
    min_tokens: int = 0  # never trim below this (0 = can be dropped entirely)


def render(template: str, slots: Dict[str, Slot], budget_tokens: int) -> str:
    """Fill a template, trimming low-priority slots until the prompt fits the budget."""
    fixed = _VAR.sub("", template)
    fixed_tokens = estimate_tokens(fixed)
    values = {k: v.text for k, v in slots.items()}

    def total() -> int:
        return fixed_tokens + sum(estimate_tokens(t) for t in values.values())

    if total() > budget_tokens:
        for name, slot in sorted(slots.items(), key=lambda kv: kv[1].priority):
            over = total() - budget_tokens
            if over <= 0:
                break
            cur = estimate_tokens(values[name])
            target = max(slot.min_tokens, cur - over)
            if target <= 0:
                values[name] = ""
            elif target < cur:
                values[name] = truncate_to_tokens(values[name], target)

    out = _VAR.sub(lambda m: values.get(m.group(1), ""), template)
    return re.sub(r"\n{4,}", "\n\n\n", out)


def files_block(files: Dict[str, str], title: str = "") -> str:
    if not files:
        return "(no files yet)"
    parts = []
    for path, content in files.items():
        if path.startswith("("):  # a note such as "(omitted)", not a real file
            parts.append("%s %s" % (path, content))
            continue
        parts.append("=== FILE: %s ===\n%s\n=== END FILE ===" % (path, content.rstrip("\n")))
    return (title + "\n" if title else "") + "\n\n".join(parts)


def fit_files(files: Dict[str, str], budget_tokens: int, focus: Optional[List[str]] = None) -> Dict[str, str]:
    """Keep focus files whole when possible; include other files while budget allows."""
    focus = focus or []
    ordered = [f for f in focus if f in files] + [f for f in files if f not in focus]
    out: Dict[str, str] = {}
    left = budget_tokens
    skipped = []
    for f in ordered:
        t = estimate_tokens(files[f]) + 20
        if t <= left:
            out[f] = files[f]
            left -= t
        elif f in focus and left > 400:
            out[f] = truncate_to_tokens(files[f], left - 40, "[... file truncated: too large for context ...]")
            left = 0
        else:
            skipped.append(f)
    if skipped:
        out["(omitted)"] = "Not shown to save context: " + ", ".join(skipped)
    return out
