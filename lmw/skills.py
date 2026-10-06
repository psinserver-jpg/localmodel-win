"""Skill loading and selection.

A skill is a directory with:
    SKILL.md        frontmatter (name, description, triggers, priority, always) + body
    checklist.md    optional; used by the review phases
    reference/*.md  optional deep-dive files, each with its own frontmatter + triggers

The format is compatible with the SKILL.md convention used by Claude Code and other
agents, plus a few extra keys (triggers, priority, always) that LMW uses for routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .textutil import estimate_tokens


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    """Parse a tiny YAML subset: `key: value` and `key: [a, b, c]`."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta: Dict[str, object] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        elif value.lower() in ("true", "false"):
            meta[key] = value.lower() == "true"
        elif re.fullmatch(r"-?\d+", value):
            meta[key] = int(value)
        else:
            meta[key] = value.strip("'\"")
    body = "\n".join(lines[end + 1:]).strip("\n")
    return meta, body


@dataclass
class Reference:
    name: str
    description: str
    triggers: List[str]
    body: str

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.body)


@dataclass
class Skill:
    name: str
    description: str
    body: str
    triggers: List[str] = field(default_factory=list)
    priority: int = 0
    always: bool = False
    checklist: str = ""
    references: List[Reference] = field(default_factory=list)
    path: Optional[Path] = None

    def score(self, text: str) -> int:
        return trigger_score(self.triggers, text)


def trigger_score(triggers: List[str], text: str) -> int:
    """Count trigger hits. ASCII triggers match on word boundaries; others (e.g. Korean) by substring."""
    low = text.lower()
    score = 0
    for t in triggers:
        t = t.lower().strip()
        if not t:
            continue
        if t.isascii():
            if re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", low):
                score += 1
        elif t in low:
            score += 1
    return score


def _as_list(value: object) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def load_skill(directory: Path) -> Optional[Skill]:
    skill_file = directory / "SKILL.md"
    if not skill_file.is_file():
        return None
    meta, body = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    checklist_file = directory / "checklist.md"
    refs: List[Reference] = []
    ref_dir = directory / "reference"
    if ref_dir.is_dir():
        for f in sorted(ref_dir.glob("*.md")):
            rmeta, rbody = parse_frontmatter(f.read_text(encoding="utf-8"))
            refs.append(
                Reference(
                    name=str(rmeta.get("name") or f.stem),
                    description=str(rmeta.get("description") or ""),
                    triggers=_as_list(rmeta.get("triggers")),
                    body=rbody,
                )
            )
    return Skill(
        name=str(meta.get("name") or directory.name),
        description=str(meta.get("description") or ""),
        body=body,
        triggers=_as_list(meta.get("triggers")),
        priority=int(meta.get("priority") or 0),  # type: ignore[arg-type]
        always=bool(meta.get("always")),
        checklist=checklist_file.read_text(encoding="utf-8").strip() if checklist_file.is_file() else "",
        references=refs,
        path=directory,
    )


def load_skills(skills_dir: Path) -> List[Skill]:
    skills = []
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        s = load_skill(d)
        if s:
            skills.append(s)
    return skills


def select_skills(
    skills: List[Skill],
    text: str,
    force: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    max_skills: int = 3,
) -> List[Skill]:
    """Pick the skills relevant to `text`. `always` skills and forced skills are always included."""
    force = [f.lower() for f in (force or [])]
    exclude = [e.lower() for e in (exclude or [])]
    chosen: List[Skill] = []
    scored: List[Tuple[int, int, Skill]] = []
    for s in skills:
        if s.name.lower() in exclude:
            continue
        if s.always or s.name.lower() in force:
            chosen.append(s)
            continue
        sc = s.score(text)
        if sc > 0:
            scored.append((sc, s.priority, s))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    for _, _, s in scored[:max_skills]:
        chosen.append(s)
    chosen.sort(key=lambda s: -s.priority)
    return chosen


def select_references(skills: List[Skill], text: str, max_refs: int = 3) -> List[Tuple[Skill, Reference]]:
    scored = []
    for s in skills:
        for r in s.references:
            sc = trigger_score(r.triggers, text)
            if sc > 0:
                scored.append((sc, s, r))
    scored.sort(key=lambda x: -x[0])
    return [(s, r) for _, s, r in scored[:max_refs]]
