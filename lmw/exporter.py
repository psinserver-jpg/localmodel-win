"""Build a single system prompt from the skills, for chat apps without the orchestrator."""

from __future__ import annotations

from typing import List, Optional

from .config import Config
from .skills import load_skills, select_skills
from .textutil import estimate_tokens, truncate_to_tokens

HEADER = """# LMW Skill Pack (system prompt)

You follow the Core Workflow Protocol below for EVERY request: think, review your
understanding, plan, review the plan, implement, then review and fix in rounds until the
Definition of Done is met. Domain skills and checklists follow; apply the ones relevant
to the request.
"""


def build_prompt(cfg: Config, names: List[str], compact: bool = False, references: bool = False,
                 for_text: str = "", budget: Optional[int] = None) -> str:
    skills = load_skills(cfg.resolved_skills_dir())
    if for_text:
        skills = select_skills(skills, for_text, force=names)
    elif names:
        wanted = {n.lower() for n in names}
        skills = [s for s in skills if s.always or s.name.lower() in wanted]
    skills.sort(key=lambda s: -s.priority)
    parts = [HEADER]
    for s in skills:
        parts.append("\n---\n\n" + s.body.strip())
        if s.checklist and (not compact or s.always):
            parts.append("\n" + s.checklist.strip())
        if references and not compact:
            for r in s.references:
                parts.append("\n" + r.body.strip())
    text = "\n".join(parts).strip() + "\n"
    if budget and estimate_tokens(text) > budget:
        text = truncate_to_tokens(text, budget)
    return text
