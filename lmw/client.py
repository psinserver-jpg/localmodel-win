"""Minimal, dependency-free chat clients for local model servers.

- "openai": any OpenAI-compatible server (Ollama /v1, LM Studio, llama.cpp server,
  vLLM, text-generation-webui, KoboldCpp, Jan, ...).
- "ollama": Ollama's native /api/chat, which lets us set num_ctx. Ollama's default
  context is small and silently truncates long prompts, which is the #1 reason local
  models "forget" the task — prefer this provider when using Ollama.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .config import Config
from .stats import STATS

Message = Dict[str, str]
TokenCallback = Optional[Callable[[str], None]]


class ModelError(RuntimeError):
    pass


@dataclass
class ChatResult:
    text: str
    finish_reason: str  # "stop", "length", or provider-specific
    usage: Optional[Dict[str, float]] = None  # prompt_tokens, completion_tokens, gen_seconds

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"


_THINK_RE = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models (Qwen3, DeepSeek-R1, ...)."""
    text = _THINK_RE.sub("", text)
    # An unclosed <think> at the start means the whole visible answer follows </think>.
    m = re.search(r"</(think|thinking|reasoning)>", text, re.IGNORECASE)
    if m and not re.search(r"<(think|thinking|reasoning)>", text[: m.start()], re.IGNORECASE):
        text = text[m.end():]
    return text.strip("\n")


def _peek(err: urllib.error.HTTPError) -> str:
    try:
        body = err.read().decode("utf-8", errors="replace")[:1000]
    except Exception:
        body = ""
    err.read = lambda *a, **k: body.encode()  # keep it readable for later error messages
    return body


def _merge_system_messages(messages: List[Message]) -> List[Message]:
    sys_text = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [dict(m) for m in messages if m["role"] != "system"]
    if sys_text and rest and rest[0]["role"] == "user":
        rest[0]["content"] = sys_text + "\n\n---\n\n" + rest[0]["content"]
    elif sys_text:
        rest.insert(0, {"role": "user", "content": sys_text})
    return rest


class ChatClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._stream_usage = True  # ask OpenAI-compatible servers for exact token usage
        self._merge_system = False  # some chat templates (e.g. older Gemma/Mistral) reject a system role

    # ------------------------------------------------------------------ public
    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        on_token: TokenCallback = None,
    ) -> ChatResult:
        temperature = self.cfg.temperature if temperature is None else temperature
        max_tokens = max_tokens or self.cfg.max_output_tokens
        last_err: Optional[Exception] = None

        def tap(piece: str) -> None:
            STATS.token(piece)
            if on_token:
                on_token(piece)

        if self._merge_system:
            messages = _merge_system_messages(messages)
        for attempt in range(4):
            STATS.begin(messages)
            try:
                if self.cfg.provider == "ollama":
                    res = self._chat_ollama(messages, temperature, max_tokens, tap)
                else:
                    res = self._chat_openai(messages, temperature, max_tokens, tap)
                STATS.finish(res.usage)
                return res
            except urllib.error.HTTPError as e:
                STATS.abort()
                detail = _peek(e)
                if e.code in (400, 422, 500) and not self._merge_system and re.search(
                        r"system|role|conversation roles|alternate", detail, re.I):
                    self._merge_system = True  # template has no system role: fold it into the user turn
                    messages = _merge_system_messages(messages)
                    last_err = e
                    continue
                if e.code in (400, 422) and self._stream_usage:
                    self._stream_usage = False  # server rejected stream_options; retry without it
                    last_err = e
                    continue
                last_err = e
                if e.code < 500:
                    break
                time.sleep(2 * (attempt + 1))
            except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
                STATS.abort()
                last_err = e
                if isinstance(e, urllib.error.HTTPError) and e.code < 500:
                    break
                time.sleep(2 * (attempt + 1))
            except BaseException:
                STATS.abort()
                raise
        raise ModelError(self._explain(last_err))

    def list_models(self) -> List[str]:
        if self.cfg.provider == "ollama":
            data = self._get_json(self._ollama_base() + "/api/tags")
            return [m.get("name", "") for m in data.get("models", [])]
        data = self._get_json(self.cfg.base_url.rstrip("/") + "/models")
        return [m.get("id", "") for m in data.get("data", [])]

    # --------------------------------------------------------------- internals
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            h["Authorization"] = "Bearer " + self.cfg.api_key
        return h

    def _ollama_base(self) -> str:
        base = self.cfg.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        return base

    def _get_json(self, url: str) -> dict:
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise ModelError(self._explain(e))

    def _post_stream(self, url: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        return urllib.request.urlopen(req, timeout=self.cfg.timeout)

    def _chat_openai(self, messages, temperature, max_tokens, on_token) -> ChatResult:
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self._stream_usage:
            body["stream_options"] = {"include_usage": True}
        parts: List[str] = []
        finish = "stop"
        usage = None
        with self._post_stream(url, body) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype and "stream" not in ctype:  # server ignored stream=true
                data = json.loads(resp.read().decode("utf-8"))
                choice = (data.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content") or choice.get("text") or ""
                if text and on_token:
                    on_token(text)
                return ChatResult(text, choice.get("finish_reason") or "stop", data.get("usage"))
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except ValueError:
                    continue
                if chunk.get("error"):
                    raise ModelError(str(chunk["error"]))
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or choice.get("message") or {}
                    piece = delta.get("content") or ""
                    if piece:
                        parts.append(piece)
                        if on_token:
                            on_token(piece)
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
        return ChatResult("".join(parts), finish, usage)

    def _chat_ollama(self, messages, temperature, max_tokens, on_token) -> ChatResult:
        url = self._ollama_base() + "/api/chat"
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": self.cfg.context_tokens,
                "num_predict": max_tokens,
            },
        }
        parts: List[str] = []
        finish = "stop"
        usage = None
        with self._post_stream(url, body) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except ValueError:
                    continue
                if chunk.get("error"):
                    raise ModelError(str(chunk["error"]))
                piece = (chunk.get("message") or {}).get("content") or ""
                if piece:
                    parts.append(piece)
                    if on_token:
                        on_token(piece)
                if chunk.get("done"):
                    finish = chunk.get("done_reason") or "stop"
                    if chunk.get("eval_count"):
                        usage = {
                            "prompt_tokens": chunk.get("prompt_eval_count") or 0,
                            "completion_tokens": chunk["eval_count"],
                            "gen_seconds": (chunk.get("eval_duration") or 0) / 1e9,
                        }
                    break
        return ChatResult("".join(parts), finish, usage)

    def _explain(self, err: Optional[Exception]) -> str:
        where = self._ollama_base() if self.cfg.provider == "ollama" else self.cfg.base_url
        if isinstance(err, urllib.error.HTTPError):
            detail = ""
            try:
                detail = err.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            hint = ""
            if err.code == 404:
                hint = " (wrong base_url, or model '%s' is not installed/loaded)" % self.cfg.model
            return "Model server returned HTTP %s%s: %s" % (err.code, hint, detail)
        return (
            "Cannot reach the model server at %s (%s). Is Ollama / LM Studio / llama.cpp running? "
            "Check --base-url and --provider." % (where, err)
        )
