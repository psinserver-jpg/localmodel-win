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


class _RunnerCrash(Exception):
    """Ollama's model process stopped (often: out of GPU memory)."""


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


class _ThinkMerger:
    """Folds a separate reasoning stream into the text as <think>...</think>, so every
    server/model looks the same downstream (the agent shows it as a collapsible block)."""

    def __init__(self):
        self.open = False

    def feed(self, thought: str, content: str) -> List[str]:
        out = []
        if thought:
            if not self.open:
                out.append("<think>")
                self.open = True
            out.append(thought)
        if content:
            if self.open:
                out.append("</think>")
                self.open = False
            out.append(content)
        return out

    def close(self) -> List[str]:
        if self.open:
            self.open = False
            return ["</think>"]
        return []


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
        self._think: Optional[bool] = None  # per call: False = ask reasoning models not to think

    # ------------------------------------------------------------------ public
    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        on_token: TokenCallback = None,
        think: Optional[bool] = None,
    ) -> ChatResult:
        """think=False asks reasoning models (Qwen3, DeepSeek-R1, …) to answer without thinking."""
        self._think = think
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
                if e.code in (400, 422) and getattr(self, "_think_kw", True) and self._think is False:
                    self._think_kw = False  # server rejected the no-thinking switch; retry without it
                    last_err = e
                    continue
                if e.code == 500 and self.is_ollama() and self._runner_crashed(detail) and self._num_ctx() > 8192:
                    self._ctx_cap = max(8192, self._num_ctx() // 2)  # less GPU memory for the KV cache
                    self._last_detail = detail
                    try:
                        from .events import emit
                        emit("notice", level="warn", text="Ollama 가 모델 실행 중 멈춰서 컨텍스트를 %dK 로 줄여 다시 시도합니다 "
                             "(GPU 메모리 부족일 가능성이 높습니다)" % (self._ctx_cap // 1024))
                    except Exception:
                        pass
                    last_err = e
                    time.sleep(1.5)
                    continue
                if e.code in (400, 422) and self._stream_usage:
                    self._stream_usage = False  # server rejected stream_options; retry without it
                    last_err = e
                    continue
                last_err = e
                if e.code < 500:
                    break
                time.sleep(2 * (attempt + 1))
            except _RunnerCrash as e:  # the model process died mid-answer
                STATS.abort()
                self._last_detail = str(e)
                if self._num_ctx() > 8192 and attempt < 3:
                    self._ctx_cap = max(8192, self._num_ctx() // 2)
                    try:
                        from .events import emit
                        emit("notice", level="warn", text="Ollama 가 답하는 중 멈춰서 컨텍스트를 %dK 로 줄여 다시 시도합니다"
                             % (self._ctx_cap // 1024))
                    except Exception:
                        pass
                    time.sleep(1.5)
                    continue
                raise ModelError(self._crash_text(str(e)))
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

    # ----------------------------------------------------- loading / unloading
    def is_ollama(self) -> bool:
        if self.cfg.provider == "ollama" or ":11434" in self.cfg.base_url:
            return True
        if not hasattr(self, "_ollama_probe"):
            try:
                self._get_json(self._ollama_base() + "/api/version")
                self._ollama_probe = True
            except Exception:
                self._ollama_probe = False
        return self._ollama_probe

    def _lms(self) -> Optional[str]:
        import shutil
        return shutil.which("lms") if ":1234" in self.cfg.base_url else None

    def load_model(self, name: str) -> bool:
        """Put a model into GPU memory now, so the first request does not wait. False = not supported."""
        if self.is_ollama():
            self._post_json(self._ollama_base() + "/api/generate",
                            {"model": name, "prompt": "", "stream": False, "keep_alive": "30m",
                             "options": {"num_ctx": self._num_ctx()}}, timeout=600)
            return True
        lms = self._lms()
        if lms:
            import subprocess
            subprocess.run([lms, "load", name, "-y"], capture_output=True, timeout=600)
            return True
        return False  # vLLM, llama.cpp, …: the server decides what is loaded

    def memory_warning(self, name: str) -> str:
        """Non-empty when the loaded model does not fully fit in GPU memory (slow, or may crash)."""
        from . import gpu
        if not self.is_ollama():
            return ""
        try:
            ps = self._get_json(self._ollama_base() + "/api/ps")
        except Exception:
            return ""
        for m in ps.get("models", []):
            if m.get("name") == name or m.get("model") == name:
                size, vram = m.get("size") or 0, m.get("size_vram") or 0
                if size and vram < size * 0.95:
                    return ("⚠ GPU 메모리 부족 — %s 의 %d%% 만 GPU 에 올라가 나머지는 CPU 에서 돌아갑니다 (느려지거나 멈출 수 있음). %s"
                            % (name, int(100 * vram / size), gpu.describe(gpu.usage())))
        return ""

    def unload_model(self, name: str) -> bool:
        """Free the GPU memory of a model that is no longer used."""
        if self.is_ollama():
            self._post_json(self._ollama_base() + "/api/generate", {"model": name, "keep_alive": 0}, timeout=60)
            return True
        lms = self._lms()
        if lms:
            import subprocess
            subprocess.run([lms, "unload", name], capture_output=True, timeout=120)
            return True
        return False

    def _crash_text(self, detail: str) -> str:
        from . import gpu
        info = gpu.usage()
        if gpu.low(info) or re.search(r"out of memory|cudaMalloc|OOM", str(detail), re.I):
            return ("⚠ GPU 메모리 부족 — 모델을 GPU 에 올릴 수 없어 Ollama 가 멈췄습니다.\n  %s\n"
                    "  해결: GPU 를 쓰는 다른 프로그램을 끄거나, 더 작은 모델(/model) 또는 작은 컨텍스트(/ctx 16384)를 쓰세요."
                    % (gpu.describe(info) or str(detail).strip()[:200]))
        return ("Ollama 가 모델을 실행하다 멈췄습니다 (%s). 흔한 원인:\n"
                "  · GPU 메모리 부족 — 다른 프로그램(vLLM, Open WebUI 의 다른 모델, 게임 등)이 GPU 를 쓰는지 nvidia-smi 로 확인\n"
                "  · Ollama 가 오래됨 — RTX 50 시리즈는 최신 Ollama 필요 (ollama --version)\n"
                "  · 컨텍스트가 큼 — /ctx 16384 로 줄여 보기\n"
                "  같은 GPU 에서 vLLM 이 이미 모델을 띄우고 있다면 /server 로 그 vLLM 을 lmw 에 연결하면 됩니다."
                % (str(detail).strip()[:200] or "EOF"))

    def _num_ctx(self) -> int:
        return min(self.cfg.context_tokens, getattr(self, "_ctx_cap", 0) or self.cfg.context_tokens)

    def _runner_crashed(self, detail: str) -> bool:
        return bool(re.search(r'"?EOF"?|runner process has terminated|out of memory|CUDA error|unexpected server status',
                              detail or "", re.I))

    def _post_json(self, url: str, body: dict, timeout: float = 60) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raise ModelError("HTTP %s: %s" % (e.code, _peek(e)))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise ModelError(self._explain(e))

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
        if getattr(self, "_think", None) is False and getattr(self, "_think_kw", True):
            body["chat_template_kwargs"] = {"enable_thinking": False}  # vLLM / SGLang / llama.cpp (Qwen3 etc.)
        think = _ThinkMerger()
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
                    # reasoning models served by vLLM / LM Studio / SGLang send thinking separately
                    thought = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    piece = delta.get("content") or ""
                    for text in think.feed(thought, piece):
                        parts.append(text)
                        if on_token:
                            on_token(text)
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
        parts += think.close()
        return ChatResult("".join(parts), finish, usage)

    def _chat_ollama(self, messages, temperature, max_tokens, on_token) -> ChatResult:
        url = self._ollama_base() + "/api/chat"
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": self._num_ctx(),
                "num_predict": max_tokens,
            },
            "keep_alive": "30m",  # keep the model in GPU memory between turns (Ollama unloads after 5 min)
        }
        if getattr(self, "_think", None) is False and getattr(self, "_think_kw", True):
            body["think"] = False  # Ollama >= 0.9: reasoning models answer directly
        think = _ThinkMerger()
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
                    if self._runner_crashed(str(chunk["error"])):
                        raise _RunnerCrash(str(chunk["error"]))
                    raise ModelError(str(chunk["error"]))
                msg = chunk.get("message") or {}
                for text in think.feed(msg.get("thinking") or "", msg.get("content") or ""):
                    parts.append(text)
                    if on_token:
                        on_token(text)
                if chunk.get("done"):
                    finish = chunk.get("done_reason") or "stop"
                    if chunk.get("eval_count"):
                        usage = {
                            "prompt_tokens": chunk.get("prompt_eval_count") or 0,
                            "completion_tokens": chunk["eval_count"],
                            "gen_seconds": (chunk.get("eval_duration") or 0) / 1e9,
                        }
                    break
        parts += think.close()
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
            if err.code == 500 and self._runner_crashed(detail or getattr(self, "_last_detail", "")):
                return self._crash_text(detail or getattr(self, "_last_detail", ""))
            if err.code == 404:
                hint = " (wrong base_url, or model '%s' is not installed/loaded)" % self.cfg.model
            return "Model server returned HTTP %s%s: %s" % (err.code, hint, detail)
        return (
            "Cannot reach the model server at %s (%s). Is Ollama / LM Studio / llama.cpp running? "
            "Check --base-url and --provider." % (where, err)
        )
