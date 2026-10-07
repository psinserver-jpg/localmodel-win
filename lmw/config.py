"""Configuration: defaults < config file < environment variables < CLI flags."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent

CONFIG_FILENAMES = ("lmw.config.json", ".lmw.json")


@dataclass
class Config:
    # Model server
    provider: str = "openai"  # "openai" (any OpenAI-compatible server) or "ollama" (native API)
    base_url: str = "http://localhost:11434/v1"
    model: str = "qwen2.5-coder:14b"
    api_key: str = ""
    timeout: int = 600

    # Generation
    context_tokens: int = 16384  # total context window of the model
    max_output_tokens: int = 4096  # tokens reserved for each answer
    temperature: float = 0.2
    review_temperature: float = 0.1
    max_continuations: int = 6  # auto "continue" when an answer is cut off

    # Workflow
    plan_rounds: int = 2  # max plan -> review cycles
    min_review_rounds: int = 2  # always do at least this many reviews of the result
    max_review_rounds: int = 5  # hard stop for review -> fix cycles
    terminal: str = "auto"  # auto (Ghostty, else Windows Terminal) | ghostty | wt | none
    permission_mode: str = "ask"  # ask | auto-edit | full
    effort: str = "auto"  # auto | low | medium | high
    interactive: bool = True  # ask the user blocking questions after analysis
    skills: List[str] = field(default_factory=list)  # force-include these skills
    exclude_skills: List[str] = field(default_factory=list)
    checks: List[str] = field(default_factory=list)  # shell commands run as automated checks
    check_timeout: int = 300

    # Paths (empty = auto-detect)
    skills_dir: str = ""
    prompts_dir: str = ""

    # Web search: optional SearXNG URL (else Brave with BRAVE_API_KEY, else DuckDuckGo)
    search_url: str = ""

    # Output
    verbose: bool = False  # stream model text to the console
    # remote control (relay runs on this computer when remote control turns on)
    remote_port: int = 8787
    remote_bind: str = "0.0.0.0"  # "127.0.0.1" = this computer only (use with a tunnel)
    remote_tunnel: str = "none"  # none | tailscale | cloudflared | ssh
    remote_tunnel_target: str = ""  # for ssh: user@server[:port]
    # live status line fields: clock, session, tokens, speed, ttft, duration, calls
    statusline: List[str] = field(default_factory=lambda: ["clock", "session", "tokens", "speed", "ttft", "duration"])

    def resolved_skills_dir(self) -> Path:
        return _resolve_dir(self.skills_dir, "skills")

    def resolved_prompts_dir(self) -> Path:
        return _resolve_dir(self.prompts_dir, "prompts")

    def input_budget(self) -> int:
        """Tokens available for the prompt after reserving room for the answer."""
        margin = max(256, self.context_tokens // 20)
        return max(1024, self.context_tokens - self.max_output_tokens - margin)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get("api_key"):
            data["api_key"] = "***"
        return data


def _resolve_dir(explicit: str, name: str) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("LMW_%s_DIR" % name.upper())
    if env:
        candidates.append(Path(env).expanduser())
    candidates += [Path.cwd() / name, REPO_DIR / name, PACKAGE_DIR / name]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    raise FileNotFoundError(
        "Could not find the '%s' directory. Run from the LMW folder or set --%s-dir / LMW_%s_DIR."
        % (name, name, name.upper())
    )


ENV_MAP = {
    "LMW_PROVIDER": "provider",
    "LMW_BASE_URL": "base_url",
    "LMW_MODEL": "model",
    "LMW_API_KEY": "api_key",
    "LMW_CONTEXT_TOKENS": "context_tokens",
    "LMW_MAX_OUTPUT_TOKENS": "max_output_tokens",
    "LMW_TEMPERATURE": "temperature",
}


def _coerce(name: str, value: Any) -> Any:
    types = {f.name: f.type for f in fields(Config)}
    t = str(types.get(name, "str"))
    if value is None:
        return None
    if t in ("int", "<class 'int'>"):
        return int(value)
    if t in ("float", "<class 'float'>"):
        return float(value)
    if t in ("bool", "<class 'bool'>"):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if t.startswith("List"):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return list(value)
    return value


def global_config_file() -> Path:
    return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "config.json"


def find_config_file(start: Optional[Path] = None) -> Optional[Path]:
    """Project config (lmw.config.json in the folder) wins over the global ~/.lmw/config.json."""
    for base in [start or Path.cwd(), REPO_DIR]:
        for name in CONFIG_FILENAMES:
            p = base / name
            if p.is_file():
                return p
    g = global_config_file()
    return g if g.is_file() else None


def load_config(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Config:
    cfg = Config()
    known = {f.name for f in fields(Config)}

    file_path = Path(path) if path else find_config_file()
    if file_path:
        if not file_path.is_file():
            raise FileNotFoundError("Config file not found: %s" % file_path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for key, value in data.items():
            if key in known:
                setattr(cfg, key, _coerce(key, value))

    for env, key in ENV_MAP.items():
        if os.environ.get(env):
            setattr(cfg, key, _coerce(key, os.environ[env]))

    for key, value in (overrides or {}).items():
        if value is not None and key in known:
            setattr(cfg, key, _coerce(key, value))

    if cfg.provider not in ("openai", "ollama"):
        from .servers import resolve
        server = resolve(cfg.provider)  # e.g. "lmstudio", "vllm", "llamacpp"
        if not server:
            raise ValueError("unknown provider %r (use openai, ollama, or a server name: lmw servers)" % cfg.provider)
        if cfg.base_url == Config().base_url:
            cfg.base_url = server.base_url
        cfg.provider = server.provider
    if cfg.max_output_tokens >= cfg.context_tokens:
        raise ValueError("max_output_tokens must be smaller than context_tokens")
    return cfg
