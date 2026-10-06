"""Every local model server LMW knows how to talk to.

LMW is model-agnostic: it never depends on a model family. Any model loaded in any of
these servers works the same way. Almost all of them speak the OpenAI-compatible
/v1/chat/completions API; Ollama additionally gets its native API so num_ctx can be set.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Server:
    key: str
    label: str
    provider: str  # "openai" (OpenAI-compatible) or "ollama" (native)
    base_url: str
    hint: str = ""

    @property
    def probe(self) -> str:
        if self.provider == "ollama":
            return self.base_url.rstrip("/") + "/api/tags"
        return self.base_url.rstrip("/") + "/models"


SERVERS: List[Server] = [
    Server("ollama", "Ollama", "ollama", "http://localhost:11434", "추천 · 컨텍스트 자동 설정"),
    Server("lmstudio", "LM Studio", "openai", "http://localhost:1234/v1", "Developer → Local Server 켜기"),
    Server("vllm", "vLLM", "openai", "http://localhost:8000/v1", "vllm serve <model>"),
    Server("sglang", "SGLang", "openai", "http://localhost:30000/v1", "python -m sglang.launch_server"),
    Server("llamacpp", "llama.cpp (llama-server)", "openai", "http://localhost:8080/v1", "llama-server -m model.gguf"),
    Server("localai", "LocalAI", "openai", "http://localhost:8080/v1", ""),
    Server("koboldcpp", "KoboldCpp", "openai", "http://localhost:5001/v1", ""),
    Server("textgen", "text-generation-webui", "openai", "http://localhost:5000/v1", "--api 옵션으로 실행"),
    Server("tabby", "TabbyAPI (exllama)", "openai", "http://localhost:5000/v1", ""),
    Server("aphrodite", "Aphrodite Engine", "openai", "http://localhost:2242/v1", ""),
    Server("jan", "Jan", "openai", "http://localhost:1337/v1", "Settings → Local API Server"),
    Server("gpt4all", "GPT4All", "openai", "http://localhost:4891/v1", "Enable Local API Server"),
    Server("mlx", "MLX-LM (Apple Silicon)", "openai", "http://localhost:8080/v1", "mlx_lm.server"),
    Server("litellm", "LiteLLM proxy", "openai", "http://localhost:4000/v1", "여러 서버를 하나로"),
    Server("lemonade", "Lemonade (AMD)", "openai", "http://localhost:8000/api/v1", ""),
    Server("llamafile", "llamafile", "openai", "http://localhost:8080/v1", ""),
    Server("docker", "Docker Model Runner", "openai", "http://localhost:12434/engines/v1", ""),
]

ALIASES = {s.key: s for s in SERVERS}


def resolve(name: str) -> Optional[Server]:
    return ALIASES.get(name.lower().replace("-", "").replace(" ", "").replace(".", ""))


def _get(url: str, timeout: float = 1.5, api_key: str = ""):
    headers = {"Authorization": "Bearer " + api_key} if api_key else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def detect(timeout: float = 1.2) -> List[Server]:
    """Servers answering on their default port right now (one entry per port)."""
    seen, found = set(), []
    for s in SERVERS:
        if s.probe in seen:
            continue
        try:
            _get(s.probe, timeout)
        except Exception:
            continue
        seen.add(s.probe)
        found.append(s)
    return found


def detect_context(provider: str, base_url: str, model: str, api_key: str = "") -> Optional[int]:
    """Ask the server how large the loaded model's context window is (best effort)."""
    base = base_url.rstrip("/")
    root = base[:-3] if base.endswith("/v1") else base
    try:
        if provider == "ollama":
            req = urllib.request.Request(root + "/api/show", data=json.dumps({"model": model}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                info = json.loads(r.read().decode("utf-8")).get("model_info", {})
            for k, v in info.items():
                if k.endswith(".context_length"):
                    return int(v)
            return None
        data = _get(base + "/models", 5, api_key)
        for m in data.get("data", []):
            if m.get("id") == model or not model:
                for key in ("max_model_len", "context_length", "max_context_length", "n_ctx"):
                    if m.get(key):
                        return int(m[key])
                meta = m.get("meta") or {}
                if meta.get("n_ctx_train"):
                    return int(meta["n_ctx_train"])
    except Exception:
        pass
    for path in ("/api/v0/models/" + model, "/props"):  # LM Studio REST, llama.cpp
        try:
            d = _get(root + path, 3, api_key)
        except Exception:
            continue
        for key in ("loaded_context_length", "max_context_length"):
            if d.get(key):
                return int(d[key])
        gs = d.get("default_generation_settings") or {}
        if gs.get("n_ctx"):
            return int(gs["n_ctx"])
    return None
