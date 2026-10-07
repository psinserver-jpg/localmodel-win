"""Sub-agents: specialist personas the main agent can hand a focused job to.

A persona is a markdown file (the Claude Code "agent" format):

    ---
    name: code-reviewer
    description: Reviews code for bugs, security and maintainability
    tools: Read, Grep, Glob, Bash        (Write/Edit => may change files; otherwise read-only)
    ---
    <the persona's instructions>

Built-in personas live in the repo's agents/ folder; yours (and those installed with `lmw agents add <repo>`)
in ~/.lmw/agents/. The model calls them through the `agent(name, task)` tool: a fresh Agent loop with the
persona's prompt runs the job and returns a short report - the main conversation stays small.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .skillhub import parse_loose, slugify

WRITERS = {"write", "edit", "multiedit", "notebookedit", "str_replace_editor", "create"}
MAX_SUB_STEPS = 14


@dataclass
class Persona:
    name: str
    description: str
    body: str
    tools: List[str] = field(default_factory=list)
    source: str = ""

    @property
    def read_only(self) -> bool:
        return not any(t.strip().lower() in WRITERS for t in self.tools)


def user_agents_dir() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "agents"


def builtin_agents_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "agents"


def parse_persona(text: str, fallback: str) -> Optional[Persona]:
    meta, body = parse_loose(text)
    if not body.strip():
        return None
    name = slugify(str(meta.get("name") or fallback))
    tools = meta.get("tools")
    tool_list = [t.strip() for t in (tools if isinstance(tools, list) else str(tools or "").split(",")) if t.strip()]
    desc = " ".join(str(meta.get("description") or "").split())
    if not desc:
        first = next((l.strip("# ").strip() for l in body.splitlines() if l.strip()), name)
        desc = first[:160]
    return Persona(name, desc[:300], body.strip(), tool_list, str(meta.get("source") or ""))


def load_agents() -> Dict[str, Persona]:
    out: Dict[str, Persona] = {}
    from . import hubcontent
    for d in (builtin_agents_dir(), hubcontent.agents_dir(), user_agents_dir()):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                p = parse_persona(f.read_text(encoding="utf-8"), f.stem)
            except OSError:
                continue
            if p and p.name not in out:  # built-ins first: a downloaded file cannot replace them
                out[p.name] = p
    return out


def find(personas: Dict[str, Persona], name: str) -> Optional[Persona]:
    n = slugify(name)
    if n in personas:
        return personas[n]
    hits = [p for k, p in personas.items() if n and (k.startswith(n) or n in k)]
    return hits[0] if len(hits) == 1 else None


def catalog(personas: Dict[str, Persona], limit: int = 12) -> str:
    """Prompt text listing the sub-agents (kept short: 12 names with a short description)."""
    if not personas:
        return ""
    rows = ["- %s: %s" % (p.name, p.description[:90]) for p in list(personas.values())[:limit]]
    more = " (+%d more: agent(\"list\"))" % (len(personas) - limit) if len(personas) > limit else ""
    return "# Sub-agents (agent(name, task) - give a complete, self-contained task)\n" + "\n".join(rows) + more


def run_sub(parent, name: str, task: str) -> Tuple[bool, str, str, Dict]:
    """Run persona `name` on `task` in a fresh agent loop and return its final report."""
    from .agent import Agent, _clip
    from .events import emit
    personas = parent.personas()
    if name.strip().lower() in ("", "list", "?", "help"):
        rows = ["%s — %s" % (p.name, p.description[:120]) for p in personas.values()]
        return True, "%d개" % len(rows), "\n".join(rows) or "No sub-agents installed.", {}
    p = find(personas, name)
    if p is None:
        sug = ", ".join(list(personas)[:12])
        return False, "하위 에이전트 없음: %s" % name, "No sub-agent %r. Available: %s" % (name, sug), {}
    if not task.strip():
        return False, "작업 내용 없음", "Give the sub-agent a task.", {}
    if getattr(parent, "sub", False):
        return False, "중첩 불가", "A sub-agent cannot start another sub-agent; do the work yourself.", {}
    child = Agent(parent.cfg, parent.root, parent.client, parent.ask_permission, parent.perms, parent.stop)
    child.sub, child.persona, child.max_steps = True, p, MAX_SUB_STEPS
    child._skills = parent._skills
    child.tools.skills = parent._skills
    emit("notice", level="info", text="↳ 하위 에이전트 %s: %s" % (p.name, " ".join(task.split())[:80]))
    try:
        answer = child.run(task, effort="low", readonly=p.read_only)
    finally:
        emit("notice", level="info", text="↳ %s 끝" % p.name)
    answer = (answer or "").strip()
    if not answer:
        return False, "%s: 답 없음" % p.name, "The sub-agent finished without a report.", {}
    return True, "%s 완료" % p.name, _clip(answer, 6000), {}


def persona_prompt(p: Persona) -> str:
    return ("# Your role: sub-agent \"%s\"\n%s\n\nYou were called by the main agent for ONE job. Do it with your tools, "
            "then finish with a SHORT report (findings, what you changed, file:line references). Do not ask the user "
            "questions and do not repeat the whole task.\n" % (p.name, p.body[:6000]))
