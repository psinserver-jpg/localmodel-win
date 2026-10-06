# localmodel-win — LMW (Local Model Workflow)

**파인튜닝 없이 로컬 모델의 성능을 끌어올리는 오픈소스 스킬 팩 + 오케스트레이터.**

로컬 모델(Qwen2.5-Coder, Llama 3, Gemma, DeepSeek-Coder, Mistral 등)은 길어지면 요청을 잊고,
중간에 코드를 생략(`// ...`)하고, 검토 없이 "완료"라고 말합니다. LMW는 Claude Code처럼
**생각 → 검토 → 계획 → 계획 검토 → 구현 → 1차 검토/수정 → 2차 검토/수정 → … → 완성**
흐름을 *모델이 아니라 프로그램이 강제*해서, 사용자가 요청한 방향을 잃지 않고 끝까지 완수하게 만듭니다.

```
 요청 ─▶ 1 THINK ─▶ 2 REVIEW ─▶ 3 PLAN ⇄ 4 REVIEW PLAN ─▶ 5 IMPLEMENT (단계별)
                                                               │
             8 DELIVER ◀── PASS ── 6 CHECKS + REVIEW ⇄ 7 FIX ◀─┘
```

## 왜 파인튜닝 없이 좋아지나

| 로컬 모델의 약점 | LMW의 보완 방법 |
|---|---|
| 요청 방향을 잃음 (drift) | **TASK ANCHOR**: 원문 요청 + 수용 기준을 *모든* 호출 맨 앞에 다시 주입 |
| 여러 단계를 스스로 못 지킴 | 오케스트레이터가 단계를 강제. 모델은 호출마다 **한 가지 일만** 함 |
| 컨텍스트가 작고 잘림 | 단계별로 필요한 것만 넣고, 실제 컨텍스트 크기에 맞춰 자동 축약. Ollama `num_ctx` 직접 설정 |
| 답변이 길면 끊김 | 출력 잘림 감지 → 자동 "이어서 작성" + 이음새 중복 제거 |
| `...`, `TODO`, lorem ipsum 생략 | 플레이스홀더 자동 탐지 → 오류로 처리, 수정 강제 |
| 자기 결과를 무조건 PASS | **실제 도구 검사**(Python 컴파일, `node --check`, HTML 태그/링크/id, CSS 괄호, JSON, 사용자 테스트 명령)가 실패하면 PASS 불가 |
| 리뷰가 관대함 | 2차 검토부터 "이전 리뷰어가 놓친 것을 찾아라" **세컨드 오피니언 모드** |
| 같은 실수 반복 | 반복 이슈/무변경 수정 감지 → "다른 접근법을 써라" 경고 |
| 웹 디자인·코딩 지식 부족 | `skills/`의 전문 스킬(디자인 토큰, 타이포, 레이아웃, 컴포넌트, 코딩/디버깅 규칙, 체크리스트)을 요청에 맞춰 자동 주입 |

## 빠른 시작 (Windows)

1. Python 3.8+ 설치 (외부 패키지 **필요 없음**)
2. 로컬 모델 서버 실행 — 예: [Ollama](https://ollama.com) 설치 후
   ```powershell
   ollama pull qwen2.5-coder:14b
   ```
3. 이 저장소를 받고 연결 확인:
   ```powershell
   git clone https://github.com/psinserver-jpg/localmodel-win
   cd localmodel-win
   .\lmw.bat doctor --provider ollama --base-url http://localhost:11434 -m qwen2.5-coder:14b
   ```
4. 실행:
   ```powershell
   .\lmw.bat run "카페 랜딩페이지 만들어줘. 메뉴, 위치, 예약 버튼 포함, 반응형" -w .\cafe --provider ollama --base-url http://localhost:11434 -m qwen2.5-coder:14b
   ```

매번 옵션을 쓰기 싫으면 `.\lmw.bat init` 으로 `lmw.config.json`을 만들고 모델명만 수정하세요.
PowerShell은 `.\lmw.ps1`, macOS/Linux는 `./lmw.sh`, 어디서나 `python -m lmw` 도 됩니다.

### 서버별 설정

| 서버 | provider | base_url |
|---|---|---|
| Ollama (권장: 컨텍스트 직접 설정) | `ollama` | `http://localhost:11434` |
| LM Studio | `openai` | `http://localhost:1234/v1` |
| llama.cpp `llama-server` | `openai` | `http://localhost:8080/v1` |
| vLLM / text-generation-webui / Jan / KoboldCpp | `openai` | 각 서버의 `/v1` 주소 |

> ⚠️ `--ctx`는 **서버에 실제로 로드된 컨텍스트 크기**와 맞추세요. LM Studio/llama.cpp는 서버 쪽에서
> 컨텍스트 길이를 설정해야 합니다. Ollama는 `--provider ollama`면 LMW가 `num_ctx`를 직접 보냅니다.

## 명령어

```text
lmw run "요청" -w 폴더        전체 워크플로 실행 (-f request.md 로 파일에서 읽기도 가능)
lmw resume -w 폴더            중단된 작업 이어서 (Ctrl+C, 서버 오류 후에도 진행상황 저장됨)
lmw skills ["샘플 요청"]       스킬 목록 / 어떤 스킬이 선택되는지 확인
lmw export -o dist/system-prompt.md   채팅 앱용 단일 시스템 프롬프트 생성
lmw check -w 폴더             자동 검사만 실행
lmw doctor                    서버 연결/모델/컨텍스트 점검
lmw init                      설정 파일 템플릿 생성
```

주요 옵션:

- `--check "pytest -q"` — 반드시 통과해야 하는 명령 (여러 번 지정 가능). 테스트가 실패하면 PASS 불가.
- `--min-rounds 2` — 최소 검토 횟수 (기본 2: 1차 검토 → 수정 → 2차 세컨드 오피니언 검토)
- `--max-rounds 5` — 최대 검토/수정 반복
- `--skill web-design` / `--no-skill coding` — 스킬 강제 포함/제외
- `--no-interactive` — 질문 없이 합리적 가정으로 진행 (기본은 꼭 필요한 질문만 물어봄)
- `-v` — 모델 출력 실시간 표시

결과물은 `-w` 폴더에, 단계별 프롬프트/응답 로그와 최종 보고서는 `폴더/.lmw/runs/<id>/`에 저장됩니다.
기존 파일을 덮어쓰면 원본이 `.lmw/runs/<id>/backup/`에 보관됩니다.

## 오케스트레이터 없이 쓰기 (Open WebUI, LM Studio 채팅 등)

```powershell
.\lmw.bat export -o dist\system-prompt.md              # 전체 스킬
.\lmw.bat export --compact -o dist\system-prompt-compact.md   # 작은 컨텍스트용
.\lmw.bat export --skill web-design -o dist\web.md     # 웹 디자인만
```

생성된 파일 내용을 채팅 앱의 **System Prompt** 칸에 붙여넣으면, 모델이 같은 단계별 프로토콜
(TASK ANCHOR, 계획 검토, 2회 이상 자기 검토, Definition of Done)을 스스로 따르도록 지시합니다.
미리 생성된 파일이 `dist/`에 들어 있습니다. 단, 단계 강제·자동 검사·자동 이어쓰기는 오케스트레이터(`lmw run`)에서만 동작하므로
작은 모델일수록 `lmw run`을 권장합니다.

`skills/` 폴더는 `SKILL.md`(name/description 프런트매터) 형식이라 SKILL.md를 읽는 다른 에이전트 도구에도 그대로 복사해 쓸 수 있습니다.

## 스킬 구성

```
skills/
  core-workflow/   항상 적용: 8단계 프로토콜, TASK ANCHOR, Definition of Done, 공통 체크리스트
  web-design/      웹사이트 디자인: 디자인 토큰, 색/대비, 타이포(한글 포함), 레이아웃, 반응형,
                   컴포넌트, 접근성, "AI스러운 디자인" 피하기 + reference/ (CSS 기반, 컴포넌트 코드, 페이지 레시피 …)
  coding/          코딩: 완전성 규칙, API 환각 방지, 오류 처리, 보안, Windows 호환, 테스트
                   + reference/ (Python, JS/TS, 테스트, 보안, 백엔드, git …)
  debugging/       디버깅: 재현→원인→가설→검증, Python/JS/Windows 흔한 오류표
```

각 스킬: `SKILL.md`(계획/구현 단계에 주입), `checklist.md`(검토 단계 채점 기준),
`reference/*.md`(요청/계획에 키워드가 있을 때만 주입 — 작은 컨텍스트 절약).

### 스킬 추가하기

`skills/<이름>/SKILL.md`:

```markdown
---
name: my-skill
description: 무엇을 하는지 + 언제 쓰는지 한 줄
triggers: [keyword, 키워드, another phrase]
priority: 30
---
# My Skill
명령형, 구체적 수치가 있는 규칙들...
```

`checklist.md`에 `- [ ]` 항목(코드를 읽어서 확인 가능한 것)을 넣으면 검토 단계에서 사용됩니다.
`prompts/*.md`의 단계별 프롬프트도 자유롭게 수정할 수 있습니다.

> 스킬 본문은 영어로 작성되어 있습니다. 로컬 모델은 영어 지시를 가장 잘 따르고 토큰도 적게 듭니다.
> 대신 결과물(설명, UI 문구)은 요청 언어(한국어)로 작성하도록 모든 단계에 지시됩니다.

## 모델 추천

- 코딩/웹: `qwen2.5-coder:14b` 이상 권장 (7B도 동작하지만 리뷰 품질이 낮아짐), `qwen3`, `deepseek-coder-v2`, `codestral`
- 컨텍스트 16K 이상 권장 (`--ctx 32768` 가능하면 더 좋음)
- 추론 모델(`<think>` 출력)도 지원 — 생각 블록은 자동 제거

## 개발

```bash
python -m unittest discover -s tests
```

MIT License.
