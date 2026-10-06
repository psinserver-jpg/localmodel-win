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


COMMANDS = [
    # (command, title, skills)
    ("lmw", "LMW: 완수 프로토콜 (생각→계획→구현→검토/수정 반복)", []),
    ("lmw-web", "LMW: 웹사이트 디자인 + 완수 프로토콜", ["web-design"]),
    ("lmw-code", "LMW: 코딩/디버깅 + 완수 프로토콜", ["coding", "debugging"]),
]

REQUEST_HEADER = "\n\n---\n\n# USER REQUEST (apply the protocol above to this request)\n\n"


def build_commands(cfg: Config, out_dir) -> List[str]:
    """Write slash-command files: Open WebUI import JSON + Markdown commands for agent CLIs."""
    import json
    import time
    from pathlib import Path

    out = Path(out_dir)
    (out / "commands").mkdir(parents=True, exist_ok=True)
    written = []
    owui = []
    for command, title, skills in COMMANDS:
        body = build_prompt(cfg, skills or ["core-workflow"], compact=True)
        # Open WebUI: typing /lmw inserts this text; the user types the request after it.
        owui.append({"command": "/" + command, "title": title, "content": body + REQUEST_HEADER,
                     "timestamp": int(time.time())})
        # Agent CLIs that read commands/<name>.md and substitute $ARGUMENTS.
        md = out / "commands" / (command + ".md")
        md.write_text("---\ndescription: %s\n---\n%s%s$ARGUMENTS\n" % (title, body, REQUEST_HEADER), encoding="utf-8")
        written.append(str(md))
    j = out / "openwebui-prompts.json"
    j.write_text(json.dumps(owui, ensure_ascii=False, indent=2), encoding="utf-8")
    written.insert(0, str(j))
    return written
