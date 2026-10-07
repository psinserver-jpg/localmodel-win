"""Slash commands imported from other tools (Claude Code style markdown prompts), stored in ~/.lmw/commands/.

    ---
    description: Review the code
    argument-hint: [pr-number]
    ---
    Review $ARGUMENTS ...

Typing /<name> <args> inside lmw sends that prompt (with $ARGUMENTS / $1..$9 filled in) to the agent.
Built-in lmw commands always win; use  /cmd <name> <args>  for an imported command with the same name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .skillhub import parse_loose, slugify, user_dir


@dataclass
class UserCommand:
    name: str
    description: str
    hint: str
    body: str
    source: str = ""


def load() -> Dict[str, UserCommand]:
    out: Dict[str, UserCommand] = {}
    d = user_dir("commands")
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.md")):
        try:
            meta, body = parse_loose(f.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not body.strip():
            continue
        name = slugify(str(meta.get("name") or f.stem))
        out[name] = UserCommand(name, " ".join(str(meta.get("description") or "").split())[:200],
                                str(meta.get("argument-hint") or ""), body.strip(), str(meta.get("source") or ""))
    return out


def expand(cmd: UserCommand, args: str) -> str:
    args = args.strip()
    parts = args.split()
    text = cmd.body.replace("$ARGUMENTS", args)
    for i in range(9, 0, -1):
        text = text.replace("$%d" % i, parts[i - 1] if len(parts) >= i else "")
    if args and "$ARGUMENTS" not in cmd.body and not re.search(r"\$[1-9]", cmd.body):
        text += "\n\nArguments: " + args
    return text
