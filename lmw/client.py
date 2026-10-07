"""Minimal, dependency-free chat clients for local model servers.

- "openai": any OpenAI-compatible server (Ollama /v1, LM Studio, llama.cpp server,
  vLLM, text-generation-webui, KoboldCpp, Jan, ...).
- "ollama": Ollama's native /api/chat, which lets us set num_ctx. Ollama's default
  context is small and silently truncates long prompts, which is the #1 reason local
  models "forget" the task — prefer this provider when using Ollama.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import netutil
from .config import Config
from .stats import STATS

Message = Dict[str, str]
TokenCallback = Optional[Callable[[str], None]]


class ModelError(RuntimeError):
    pass


def _tool_call_text(tc: Dict) -> str:
    """A native tool call -> the <tool_call> text format the agent parses."""
    f = tc.get("function") or tc
    args = f.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except ValueError:
            args = {"_raw": args}
    return "\n<tool_call>\n%s\n</tool_call>\n" % json.dumps({"name": f.get("name", ""), "arguments": args}, ensure_ascii=False)


MIN_CTX = 4096  # the smallest context lmw will fall back to after crashes


class ContextRefit(Exception):
    """The model process crashed: the caller should rebuild a smaller prompt and try again."""


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
        self._ctx_cap = self._load_cap()  # a context size that crashed before is not tried again

    # ------------------------------------------------------------------ public
    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        on_token: TokenCallback = None,
        think: Optional[bool] = None,
        refit: bool = False,
        tools: Optional[List[Dict]] = None,
    ) -> ChatResult:
        """think=False asks reasoning models (Qwen3, DeepSeek-R1, …) to answer without thinking.
        refit=True: on a model-process crash raise ContextRefit, so the caller rebuilds a smaller prompt."""
        self._think = think
        self._tools = tools if getattr(self, "_tools_ok", True) else None
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
            est = STATS.current.prompt_tokens if STATS.current else 0
            try:
                if self.cfg.provider == "ollama" and not getattr(self, "_compat", False):
                    res = self._chat_ollama(messages, temperature, max_tokens, tap)
                else:
                    res = self._chat_openai(messages, temperature, max_tokens, tap)
                STATS.finish(res.usage)
                real = int((res.usage or {}).get("prompt_tokens") or 0)
                if real and est > 200:  # learn how our token estimate compares with the server's count
                    self.token_ratio = max(1.0, min(3.0, 0.5 * self.token_ratio + 0.5 * real / est))
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
                if e.code in (400, 422, 500) and self._tools and re.search(r"tool", detail, re.I):
                    self._tools_ok = False  # this model/server has no native tool calling: tools stay in the prompt
                    self._tools = None
                    last_err = e
                    continue
                if e.code in (400, 422) and getattr(self, "_think_kw", True) and self._think is False:
                    self._think_kw = False  # server rejected the no-thinking switch; retry without it
                    last_err = e
                    continue
                if e.code == 500 and self.is_ollama() and self._runner_crashed(detail) and refit and attempt < 2:
                    self._last_detail = detail
                    self._shrink()
                    raise ContextRefit(detail)
                if e.code == 500 and self.is_ollama() and self._runner_crashed(detail) and self._num_ctx() > MIN_CTX:
                    self._set_cap(self._num_ctx() // 2)  # less GPU memory for the KV cache
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
                if refit and getattr(self, "_refits", 0) < 2:
                    self._refits = getattr(self, "_refits", 0) + 1
                    self._shrink()
                    raise ContextRefit(str(e))
                if self._num_ctx() > MIN_CTX and attempt < 3:
                    self._set_cap(self._num_ctx() // 2)
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
        where = gpu.describe(info)
        log = gpu.ollama_log_errors()
        if log:  # Ollama's own log says why: show that instead of guesses
            return ("Ollama 가 모델을 실행하다 멈췄습니다 (%s). Ollama 로그의 마지막 오류:\n%s\n"
                    "  이 줄을 그대로 알려주시면 원인을 찾을 수 있습니다.%s"
                    % (str(detail).strip()[:120] or "EOF", log, ("\n  현재 GPU — " + where) if where else ""))
        return (("현재 GPU — %s\n  " % where if where else "") + "Ollama 가 모델을 실행하다 멈췄습니다 (%s). 흔한 원인:\n"
                "  · GPU 메모리 부족 — 다른 프로그램(vLLM, Open WebUI 의 다른 모델, 게임 등)이 GPU 를 쓰는지 nvidia-smi 로 확인\n"
                "  · Ollama 가 오래됨 — RTX 50 시리즈는 최신 Ollama 필요 (ollama --version)\n"
                "  · 컨텍스트가 큼 — /ctx 16384 로 줄여 보기\n"
                "  같은 GPU 에서 vLLM 이 이미 모델을 띄우고 있다면 /server 로 그 vLLM 을 lmw 에 연결하면 됩니다."
                % (str(detail).strip()[:200] or "EOF"))

    token_ratio = 1.15  # real tokens per estimated token (paths, Korean, code count more); learned per server

    def prompt_budget(self) -> int:
        """Estimated-token budget for a prompt, so the REAL prompt fits in the context sent to the server."""
        ctx = self._num_ctx()
        room = ctx - min(self.cfg.max_output_tokens, ctx // 3) - max(256, ctx // 12)
        return max(1024, int(room / self.token_ratio))

    # ---- learned context cap (per model + server, kept in ~/.lmw/ctx-cap.json)
    def _cap_key(self) -> str:
        return "%s|%s" % (self.cfg.model, self.cfg.base_url if hasattr(self.cfg, "base_url") else "")

    def _cap_file(self) -> Path:
        return Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "ctx-cap.json"

    def _load_cap(self) -> int:
        try:
            return int(json.loads(self._cap_file().read_text(encoding="utf-8")).get(self._cap_key(), 0))
        except Exception:
            return 0

    def _set_cap(self, tokens: int) -> None:
        self._ctx_cap = max(MIN_CTX, int(tokens) // 1024 * 1024)
        try:
            f = self._cap_file()
            data = {}
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
            data[self._cap_key()] = self._ctx_cap
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def reset_server(self) -> None:
        """The server (or its address) changed: forget what was learned about the old one."""
        self._compat = False
        self._tools = None
        self._ctx_cap = self._load_cap()

    def forget_cap(self) -> None:
        """`/context` set by hand: drop what was learned from crashes."""
        self._ctx_cap = 0
        try:
            f = self._cap_file()
            data = json.loads(f.read_text(encoding="utf-8"))
            data.pop(self._cap_key(), None)
            f.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _shrink(self) -> None:
        """After a crash: a smaller context, and expect more tokens per estimate."""
        self.token_ratio = min(3.0, self.token_ratio * 1.3)
        if self.cfg.provider == "ollama" and not getattr(self, "_compat", False):
            self._compat = True  # next try: Ollama's OpenAI-compatible endpoint (a different code path in Ollama)
        if self._num_ctx() > MIN_CTX:
            self._set_cap(self._num_ctx() * 3 // 4)

    def _num_ctx(self) -> int:
        return min(self.cfg.context_tokens, getattr(self, "_ctx_cap", 0) or self.cfg.context_tokens)

    def _runner_crashed(self, detail: str) -> bool:
        return bool(re.search(r'"?EOF"?|runner process has terminated|out of memory|CUDA error|unexpected server status',
                              detail or "", re.I))

    def _post_json(self, url: str, body: dict, timeout: float = 60) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=self._headers())
        try:
            with netutil.urlopen(req, timeout=timeout) as resp:
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
            with netutil.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise ModelError(self._explain(e))

    def _post_stream(self, url: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        return netutil.urlopen(req, timeout=self.cfg.timeout)

    def _chat_openai(self, messages, temperature, max_tokens, on_token) -> ChatResult:
        base = self._ollama_base() + "/v1" if self.cfg.provider == "ollama" else self.cfg.base_url.rstrip("/")
        url = base + "/chat/completions"
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
        if getattr(self, "_tools", None):
            body["tools"] = self._tools
        calls: Dict[int, Dict] = {}
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
                text += "".join(_tool_call_text(tc) for tc in (choice.get("message") or {}).get("tool_calls") or [])
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
                    for tc in delta.get("tool_calls") or []:  # streamed in pieces: name first, arguments in parts
                        c = calls.setdefault(int(tc.get("index", len(calls))), {"name": "", "arguments": ""})
                        f = tc.get("function") or {}
                        c["name"] += f.get("name") or ""
                        c["arguments"] += f.get("arguments") or ""
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
        parts += think.close()
        for i in sorted(calls):
            parts.append(_tool_call_text({"function": calls[i]}))
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
        if getattr(self, "_tools", None):
            body["tools"] = self._tools  # native function calling: much more reliable for tool-trained models
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
                for tc in msg.get("tool_calls") or []:
                    parts.append(_tool_call_text(tc))
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
