"""First-run setup wizard: find a local model server, pick a model, save settings.

Runs automatically the first time `lmw` starts without any config, or with /setup.
Settings are saved to ~/.lmw/config.json (used from every folder).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

from . import ui
from .client import ChatClient, ModelError
from .config import Config
from .servers import SERVERS, detect, detect_context

GLOBAL_CONFIG = Path(os.environ.get("LMW_HOME") or (Path.home() / ".lmw")) / "config.json"

CTX_CHOICES = [(8192, "8K — 작은 모델 / 적은 VRAM"), (16384, "16K — 권장"), (32768, "32K — 큰 작업, VRAM 여유")]


def needs_setup() -> bool:
    from .config import find_config_file
    return find_config_file() is None and not os.environ.get("LMW_MODEL")


def run_wizard(cfg: Config) -> bool:
    ui.box("LMW 처음 설정", ["로컬 모델 서버를 찾고 모델을 고릅니다.", "설정은 %s 에 저장됩니다." % GLOBAL_CONFIG])
    ui.info("실행 중인 모델 서버를 찾는 중…")
    found = detect()
    servers = list(found) + [x for x in SERVERS if x not in found]
    options = [("%s ✔ 실행 중" % x.label, x.base_url) if x in found else (x.label, x.hint or x.base_url) for x in servers]
    options.append(("직접 입력", "다른 PC / 다른 포트 / 클라우드 OpenAI 호환 API"))
    if not found:
        ui.warn("실행 중인 서버가 없습니다. 아무 서버나 실행한 뒤 다시 하거나, 목록에서 고르세요.")
    i = ui.menu("모델 서버를 선택하세요 (어떤 모델이든 그대로 동작합니다)", options, 0)
    if i < 0:
        return False
    if i == len(servers):
        url = ui.read_line("  서버 주소 (예: http://192.168.0.10:11434 또는 http://host:8000/v1) > ").strip()
        if not url:
            return False
        cfg.base_url = url
        cfg.provider = "openai" if "/v1" in url else "ollama"
        key = ui.read_line("  API 키 (없으면 Enter) > ").strip()
        if key:
            cfg.api_key = key
    else:
        cfg.provider, cfg.base_url = servers[i].provider, servers[i].base_url

    try:
        models = [m for m in ChatClient(cfg).list_models() if m]
    except ModelError as e:
        ui.err(str(e))
        models = []
    if models:
        j = ui.menu("사용할 모델을 선택하세요", [(m, "") for m in models[:20]], 0)
        if j < 0:
            return False
        cfg.model = models[j]
    else:
        name = ui.read_line("  모델 이름 (예: qwen2.5-coder:14b) > ").strip()
        if name:
            cfg.model = name

    detected = detect_context(cfg.provider, cfg.base_url, cfg.model, cfg.api_key)
    if detected:
        ui.ok("모델 컨텍스트: %d 토큰 (서버에서 확인)" % detected)
    default = 1
    if detected:
        default = max([i for i, (c, _) in enumerate(CTX_CHOICES) if c <= detected] or [0])
    k = ui.menu("사용할 컨텍스트 크기", [("%dK" % (c // 1024), h) for c, h in CTX_CHOICES], default)
    if k >= 0:
        cfg.context_tokens = CTX_CHOICES[k][0]
        cfg.max_output_tokens = min(4096, cfg.context_tokens // 3)
    save_global(cfg)
    ui.ok("저장 완료 — 언제든 /setup 으로 다시 설정할 수 있습니다")
    return True


def save_global(cfg: Config, path: Optional[Path] = None) -> Path:
    path = path or GLOBAL_CONFIG
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            data = {}
    if cfg.api_key:
        data["api_key"] = cfg.api_key
    data.update({"provider": cfg.provider, "base_url": cfg.base_url, "model": cfg.model,
                 "context_tokens": cfg.context_tokens, "max_output_tokens": cfg.max_output_tokens})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
