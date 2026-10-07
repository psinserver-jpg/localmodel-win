"""One-line way to point lmw at a model server: another PC, another port, or a cloud OpenAI-compatible API.

    192.168.0.10            -> tries the usual ports there (Ollama 11434, LM Studio 1234, vLLM 8000, ...)
    192.168.0.10:1234       -> asks that port which kind of server it is
    :8000                   -> the same on this computer
    lmstudio / vllm / ...   -> a known server on its default port
    https://host/v1 [key]   -> cloud / any OpenAI-compatible API (the key is asked for when it is needed)
    openai | openrouter | groq | together | deepseek | gemini   -> well known cloud services (asks for the key)
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .servers import SERVERS, _get, resolve

CLOUD = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "mistral": "https://api.mistral.ai/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
}
# ports to try on a bare host, most common first
PORTS = [("ollama", 11434), ("openai", 1234), ("openai", 8000), ("openai", 8080), ("openai", 5000),
         ("openai", 1337), ("openai", 4891), ("openai", 5001), ("openai", 30000), ("openai", 4000)]


def probe(base: str, api_key: str = "", timeout: float = 1.5) -> Optional[Tuple[str, str]]:
    """What is listening at `base`?  -> (provider, base_url) or None.  Raises PermissionError on 401/403."""
    base = base.rstrip("/")
    tries = [("ollama", base, base + "/api/tags")]
    root = re.sub(r"/v1$", "", base)
    if not base.endswith("/v1"):
        tries.append(("openai", base + "/v1", base + "/v1/models"))
    tries.append(("openai", base, base + "/models"))
    if root != base:
        tries.insert(0, ("ollama", root, root + "/api/tags"))
    for provider, url, check in tries:
        try:
            d = _get(check, timeout, api_key)
        except Exception as e:
            code = getattr(e, "code", 0)
            if code in (401, 403):
                raise PermissionError(base)
            continue
        if provider == "ollama" and isinstance(d, dict) and "models" in d:
            return "ollama", url
        if provider == "openai" and isinstance(d, dict) and ("data" in d or "object" in d):
            return "openai", url
    return None


def parse(text: str) -> Tuple[str, str]:
    """-> (address, api_key) from 'address [key]' (the key may also be given as key=...)."""
    parts = text.split()
    addr = parts[0] if parts else ""
    key = ""
    for p in parts[1:]:
        key = p.split("=", 1)[1] if p.lower().startswith(("key=", "apikey=")) else p
    return addr, key


def resolve_target(text: str, api_key: str = "", log=lambda s: None) -> Tuple[Optional[Tuple[str, str]], str, str]:
    """Turn what the user typed into (provider, base_url).

    Returns (result_or_None, api_key, problem).  problem == 'key' means the server wants an API key."""
    addr, key = parse(text)
    key = key or api_key
    addr = addr.strip()
    if not addr:
        return None, key, "empty"
    low = addr.lower()
    if low in CLOUD:
        return ("openai", CLOUD[low]), key, ("" if key else "key")
    srv = resolve(low)
    if srv is not None:
        return (srv.provider, srv.base_url), key, ""
    if re.fullmatch(r":\d{2,5}", addr):  # ':1234' = a port on this computer
        addr = "localhost" + addr
    if not re.match(r"https?://", addr):
        host_only = not re.search(r":\d{2,5}(/|$)", addr) and "/" not in addr
        scheme = "http://"
        if host_only:
            log("%s 에서 모델 서버를 찾는 중…" % addr)
            for kind, port in PORTS:
                try:
                    hit = probe("%s%s:%d" % (scheme, addr, port), key)
                except PermissionError:
                    return (kind, "%s%s:%d" % (scheme, addr, port) + ("" if kind == "ollama" else "/v1")), key, "key"
                if hit:
                    return hit, key, ""
            return None, key, "notfound"
        addr = scheme + addr
    try:
        hit = probe(addr, key, 4)
    except PermissionError:
        guess = "openai" if "/v1" in addr or "api." in addr else "ollama"
        return (guess, addr.rstrip("/")), key, "key"
    if hit:
        return hit, key, ""
    if addr.startswith("https://") or "/v1" in addr:  # cloud / proxies often do not list models without a key
        return ("openai", addr.rstrip("/")), key, "" if key else "key"
    return None, key, "notfound"


def apply(cfg, text: str, ask_key=None, log=lambda s: None) -> Tuple[bool, str]:
    """Point `cfg` at the server described by `text`. ask_key() -> str is called once when a key is needed."""
    res, key, problem = resolve_target(text, cfg.api_key, log)
    if problem == "key" and not key and ask_key:
        key = (ask_key() or "").strip()
        if key and res:
            try:
                hit = probe(res[1], key, 6)
                if hit:
                    res = hit
            except PermissionError:
                return False, "API 키가 맞지 않습니다"
    if res is None:
        return False, ("서버를 찾지 못했습니다: %s — 주소/포트를 확인하세요 (예: 192.168.0.10, 192.168.0.10:1234, :8000, openai)" % text.split()[0]
                       if text.split() else "주소를 입력하세요")
    cfg.provider, cfg.base_url = res
    if key:
        cfg.api_key = key
    return True, "%s (%s)" % (cfg.base_url, "Ollama" if cfg.provider == "ollama" else "OpenAI 호환")
