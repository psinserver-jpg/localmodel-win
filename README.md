# LMW — 로컬 모델을 끝까지 일하게 만드는 CLI

로컬 LLM이 요청을 잊거나 중간에 대충 끝내지 않도록,
**생각 → 계획 → 구현 → 검토·수정 반복 → 완성**을 프로그램이 강제합니다. 파인튜닝 필요 없음.

## 1. 설치 (한 줄)

**Windows** — 명령 프롬프트(cmd) 또는 PowerShell 어디서나
```bat
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.ps1 | iex"
```
**macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.sh | sh
```

## 2. 실행

새 터미널에서 작업할 폴더로 이동한 뒤:
```
lmw
```
`lmw` 는 **[Ghostty](https://ghostty.org)** 창(LMW 전용 테마)에서 열립니다. Ghostty 가 없으면 Windows 에서는 같은 테마의 Windows Terminal 창으로 열립니다. 지금 창에서 쓰려면 `lmw --here`.

1. **로그인** — [psin.ai.kr](https://psin.ai.kr) 링크가 열리면 **Google 로그인** → **[로그인 승인하기]**
2. **모델 설정** — 실행 중인 서버(Ollama, LM Studio, vLLM 등)를 자동으로 찾아 줍니다 → 모델 선택
3. **요청 입력** — 끝!

```
> /plan 카페 홈페이지 만들어줘. 메뉴, 위치, 예약 버튼 포함

◆ 3/8 계획 — 1차
  ⎿  계획: 구현 3단계
     · 페이지 뼈대와 메뉴  (index.html)
     · 스타일  (style.css)
     · 예약 폼 동작  (app.js)

◆ 5/8 구현 — 단계 1/3: 페이지 뼈대와 메뉴
● Write(index.html)
  ⎿  저장됨
```

## 3. 쓰는 법

그냥 말하듯 입력하면 됩니다. lmw 가 알아서 파일을 **찾고(Grep·Glob) → 읽고(Read) → 고치고(Edit·Write) → 실행해서 확인(Bash)** 하고, 필요하면 **웹 검색(WebSearch)·페이지 읽기(WebFetch)** 도 합니다.

```
> calc.py 의 add 버그 고쳐줘

✻ 생각함 (1.2초)

● Read(calc.py)
  ⎿  4줄 읽음

● Edit(calc.py)
  ⎿  +1 −1
          2 -     return a-b
          2 +     return a+b

● Bash(python calc.py)
  ⎿  exit 0

● 고쳤습니다. add 가 이제 더하기를 합니다.
```

Claude Code 처럼 입력 박스(`/` 입력 시 명령 자동완성), **작업 중에 입력하면 그 내용이 작업에 바로 추가**(순서대로 처리), **Shift+Tab** 으로 권한 모드 전환, 파일 수정 전 **변경 미리보기 + 방향키 선택 메뉴**(예 · 다시 묻지 않기 · 아니요)가 나옵니다.

| 상황 | 동작 |
|---|---|
| "안녕" 같은 짧은 말 | 생각 없이 바로 답변 |
| 질문·간단한 요청 | 생각 없이 바로 답변 (필요하면 파일 읽기) |
| 코드 작성·수정·버그 수정 | 생각하고 진행 |
| `/plan 요청` (또는 `/plan` 입력 후 요청) | **계획 모드**: 분석 → 계획 → 구현 → 검토·수정 반복을 자동으로 끝까지 |

### 채팅 안에서 쓰는 `/명령` (입력창에 `/` 를 치면 자동완성)

**작업**

| 명령 | 설명 |
|---|---|
| `/run 요청` | 에이전트로 작업 (파일 읽기·쓰기·명령 실행) |
| `/plan 요청` | 계획 모드: 분석 → 계획 → 구현 → 검토·수정을 끝까지 자동으로 |
| `/ask 질문` | 질문만 하기 (읽기 전용, 파일 변경 없음) |
| `/new` | 새 세션 시작 |
| `/sessions` · `/continue` | 지난 세션 목록에서 골라 이어서 · 가장 최근 세션 이어서 |
| `/resume` | 중단된 작업 이어하기 |
| `/undo` | 마지막 작업 되돌리기 |
| `/compact` | 대화를 요약해 컨텍스트 비우기 (가득 차기 전에 자동으로도 함) |
| `/files` · `/diff` · `/check` | 프로젝트 파일 보기 · git 변경 요약 · 자동 검사 실행 |

**모델**

| 명령 | 설명 |
|---|---|
| `/model` | 모델 선택 |
| `/server 주소` | 모델 서버 변경: `192.168.0.10` · `192.168.0.10:1234` · `:8000` · `openai` · `https://…/v1 키` (종류·포트 자동 판별) |
| `/setup` | 처음 설정 다시 하기 |
| `/ctx 32768` | 컨텍스트 크기 직접 지정 (모델이 죽으면 자동으로 줄이고 기억해 둠) |
| `/memory` | 계정에 저장되는 긴 기억: `on` · `off` · `clear` · 상태 보기 |
| `/skills` · `/skill 이름` | 스킬 목록 · 특정 스킬을 항상 포함 |

**설정**

| 명령 | 설명 |
|---|---|
| `/mode` (Shift+Tab) | 권한: 매번 묻기 · 편집 자동 수락 · 전체 허용 (위험한 명령은 항상 물어봄) |
| `/effort` | 생각 수준: 자동 · 빠르게 · 보통 · 깊게 |
| `/auto` | 파일 변경 자동 승인 켜기/끄기 |
| `/rounds 5` | 최대 검토·수정 횟수 |
| `/verbose` · `/stats` · `/statusline` · `/config` | 모델 출력 실시간 보기 · 시간·토큰 통계 · 상태줄 항목 · 현재 설정 |
| `/engine` | 에이전트 엔진 선택 (lmw / aider) |

**도구 (스킬·에이전트·MCP)**

| 명령 | 설명 |
|---|---|
| `/tools` | 쓸 수 있는 도구·스킬·하위 에이전트·MCP 전체 보기 |
| `/mcp` | MCP 서버 연결: `add 이름` · `list` · `tools` · `remove` |
| `/agents` | 하위 에이전트: `list` · `add <GitHub 주소>` · `remove` |
| `/cmds` · `/cmd 이름 인자` | 가져온 슬래시 명령 목록 · 실행 |
| `/add <GitHub 주소>` | 저장소에서 스킬·에이전트·명령을 한 번에 설치 |
| `/find 검색어` | awesome-claude-code 목록에서 도구 찾기 |

**계정·기타**

| 명령 | 설명 |
|---|---|
| `/watch` | 내 계정의 다른 컴퓨터 lmw 화면 보기·조작 |
| `/web` | 이 화면을 웹에서 보는 주소 |
| `/update` | 최신 버전으로 업데이트 후 자동 재시작 |
| `/logout` | 로그아웃 |
| `/help` · `/exit` | 도움말 · 종료 |
| `Alt+Enter` | 줄바꿈 |

### 터미널에서 쓰는 `lmw 명령`

| 명령 | 설명 |
|---|---|
| `lmw` (또는 `lmw chat`) | 대화형 에이전트 시작 |
| `lmw run "요청"` · `lmw resume` | 한 번에 작업 실행 · 중단된 작업 이어서 |
| `lmw login` · `lmw logout` | Google 로그인(psin.ai.kr) · 로그아웃 |
| `lmw update` | 최신 버전으로 업데이트 |
| `lmw sync` | 허브에서 최신 스킬·하위 에이전트 받기 |
| `lmw skills [add\|remove\|list]` | 스킬 목록 · GitHub 저장소에서 설치 · 제거 (`--defaults` 로 추천 묶음) |
| `lmw agents` · `lmw cmds` | 하위 에이전트 · 가져온 슬래시 명령 |
| `lmw add <GitHub 주소>` | 스킬·에이전트·명령을 한 번에 설치 |
| `lmw find 검색어` | awesome-claude-code 목록 검색 |
| `lmw mcp [add\|list\|tools\|remove\|presets]` | MCP 서버 관리 (`add --defaults` 로 추천 5종) |
| `lmw tools` | 도구 전체 보기 |
| `lmw watch` | 다른 컴퓨터의 lmw 화면 보기 |
| `lmw ssh` · `lmw ssh-install` · `lmw tunnel` | 다른 컴퓨터에서 lmw 실행 · 설치 · 그 PC의 모델 서버 쓰기 |
| `lmw setup` · `lmw doctor` · `lmw servers` | 처음 설정 · 모델 서버 연결 점검 · 지원 서버 목록 |
| `lmw check` · `lmw init` · `lmw export` · `lmw commands` | 자동 검사 · 설정 파일 만들기 · 채팅 앱용 프롬프트 내보내기 · 슬래시 명령 만들기 |

`lmw` 가 켜져 있으면 [psin.ai.kr](https://psin.ai.kr) 에서 **＋ 새 세션** 을 눌러 같은 lmw 안에 세션을 더 열 수 있습니다 (터미널 세션은 그대로).
[psin.ai.kr](https://psin.ai.kr) 에 같은 Google 계정으로 로그인하면 세션별 대화, 생각/작업 펼쳐보기, 권한 승인, 프롬프트 보내기를 폰에서도 할 수 있습니다.

## 도구 · 스킬 · 에이전트 · MCP · 기억

- **내장 도구**: 폴더/이동/복사/삭제, 여러 파일 읽기, tree, calc, python, serve, download, git, todo, remember/recall, ask_user … 모델이 필요할 때 스스로 꺼내 씁니다 (`/tools`).
- **스킬 · 하위 에이전트**: 저장소가 아니라 **LMW Hub(psin.ai.kr)에서 받아옵니다.** lmw 를 켤 때 자동으로(6시간마다), 또는 `lmw sync` 로 바로 받고, 오프라인이면 마지막으로 받은 것을 씁니다. 디자인·three.js 스킬 등이 들어 있습니다.
- **기억**: 요청이 끝날 때마다, 그리고 컨텍스트를 요약해 비울 때 사라지는 원문을 **내 계정에 자동 저장**하고, 새 요청이 오면 관련된 옛 대화를 **자동으로 찾아 프롬프트에 넣습니다.** 컨텍스트를 키우지 않고도 긴 작업·다른 날·다른 컴퓨터의 대화를 이어갑니다. 계정마다 따로 저장되며 다른 사용자는 볼 수 없고, API 키·토큰·비밀번호 같은 값은 저장 전에 지웁니다. `/memory off` 로 끄고 `/memory clear` 로 전부 지웁니다.
- **모델이 멈추면**: 컨텍스트를 줄여 다시 시도하고, 줄인 크기를 모델별로 기억합니다. 그래도 멈추면 그 단계만 추론을 끄고 이어갑니다.
- **작업 폴더 자동 정리**: 폴더를 정하지 않고(홈·바탕화면·문서·다운로드 등에서) lmw 를 켜면 `문서/lmw` 에서 시작하고, 요청을 보면 이름을 요약해 `문서/lmw/<작업 이름>` 폴더를 만들어 거기서 작업합니다. 프로젝트 폴더 안에서 켜거나 `-w 폴더` 를 주면 그 폴더에서 그대로 작업합니다 (`LMW_NO_AUTO_FOLDER=1` 로 끄기, `LMW_PROJECTS_DIR` 로 위치 바꾸기).
- **서버 연결**: `/server` 한 줄이면 됩니다 — `192.168.0.10`(다른 PC, 포트 자동 탐색) · `192.168.0.10:1234`(포트 지정, 종류 자동 판별) · `:8000`(이 PC의 다른 포트) · `openai` / `openrouter` / `groq`(클라우드, API 키만 물어봄) · `https://주소/v1 키`.
- **시스템 언어로 답하기**: 설정의 `language` 또는 환경변수 `LMW_LANG`.
- 라이선스: Composio·bear2u 스킬은 포함하지 않고 직접 설치하며, awesome-claude-code(CC BY-NC-ND)는 파일을 담지 않고 `lmw find` 로 실시간 검색만 합니다.

## 준비물

- 로컬 모델 서버 하나: [Ollama](https://ollama.com) (추천), LM Studio, vLLM, llama.cpp, SGLang, LocalAI, KoboldCpp, Jan, GPT4All 등 17종 — 목록은 `lmw servers`
- 모델은 무엇이든 됩니다. 처음이라면 `ollama pull qwen2.5-coder:14b`

---

<details>
<summary>고급 기능</summary>

- `lmw run "요청" -w 폴더` — 대화 없이 8단계로 한 번에 실행 · `--check "pytest -q"` 테스트 통과까지 강제
- 웹 검색: 기본은 DuckDuckGo·Bing (키 필요 없음). 설정에 `"search_url": "http://localhost:8080"`(SearXNG) 또는 환경변수 `BRAVE_API_KEY` 를 넣으면 그쪽을 먼저 사용
- 답변 언어: 기본은 **요청이 한글이면 한국어, 아니면 이 컴퓨터의 시스템 언어**. 모델이 영어로 답하면 자동으로 번역해서 보여줍니다. 고정하려면 설정에 `"language": "Korean"` (또는 `en`, `ja`), 환경변수 `LMW_LANG=ko`
- 검색은 [ripgrep](https://github.com/BurntSushi/ripgrep) 이 있으면 자동 사용 · `/engine aider` 로 [Aider](https://github.com/Aider-AI/aider) 엔진 사용 가능 (`pip install aider-chat`)
- `lmw export` — 채팅 앱(Open WebUI 등)용 시스템 프롬프트 · `lmw commands` — `/lmw` 슬래시 명령 파일
- `lmw ssh user@서버` — 다른 컴퓨터에서 실행 · `lmw tunnel user@서버` — 다른 PC의 GPU 모델 사용
- `skills/` — 웹 디자인·코딩·디버깅 스킬 (SKILL.md 형식, 직접 추가 가능) · `prompts/` — 단계별 프롬프트
</details>

MIT License
